import os
import networkx as nx

class CodeGenerator:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        
    def generate(self, base_filename):
        # Build DAG
        G = nx.DiGraph()
        node_map = {n.id: n for n in self.pipeline.nodes}
        for n in self.pipeline.nodes:
            G.add_node(n.id)
        for e in self.pipeline.edges:
            G.add_edge(e.source, e.target)
            
        # Find sources (in-degree 0) and sinks (out-degree 0 or output/visualization)
        # We skip 'transfer' nodes for path calculation
        proc_nodes = [n for n in self.pipeline.nodes if n.type != 'transfer']
        proc_ids = [n.id for n in proc_nodes]
        G_proc = G.subgraph(proc_ids).copy()
        
        sources = [n for n in G_proc.nodes if G_proc.in_degree(n) == 0]
        end_nodes = [n for n in G_proc.nodes if G_proc.out_degree(n) == 0]
        if not end_nodes:
            end_nodes = list(G_proc.nodes) # fallback
            
        all_paths = []
        for src in sources:
            for end in end_nodes:
                if nx.has_path(G_proc, src, end):
                    paths = list(nx.all_simple_paths(G_proc, src, end))
                    all_paths.extend(paths)
                
        # If there are no paths (e.g. disconnected nodes), fallback to topological sort
        if not all_paths:
            all_paths = [list(nx.topological_sort(G))]
            
        generated_files = []
        
        for i, path in enumerate(all_paths):
            suffix = f"_path{i+1}" if len(all_paths) > 1 else ""
            filepath = base_filename.replace('.m', f'{suffix}.m')
            
            code = self._generate_script_for_path(path, node_map)
            with open(filepath, 'w') as f:
                f.write(code)
            generated_files.append(filepath)
            
        return generated_files

    def _generate_script_for_path(self, path, node_map):
        settings = self.pipeline.settings
        
        code = []
        code.append("%% EEGLAB-DAG Generated Pipeline")
        code.append("clear; clc; close all;")
        code.append("")
        
        code.append("%% INITIALIZE PARAMETERS")
        code.append("param = struct();")
        code.append(f"param.openWeb = {str(settings.get('generate_report', True)).lower()};")
        code.append(f"param.path_globalSavepath = '{settings.get('global_savepath', '')}';")
        code.append("")
        
        node_counts = {}
        path_nodes = []
        
        for node_id in path:
            node = node_map[node_id]
            func = node.function
            if func not in node_counts:
                node_counts[func] = 1
            else:
                node_counts[func] += 1
                
            unique_id = f"{func}_{node_counts[func]}"
            path_nodes.append((unique_id, node))
            
            if node.type == 'input' or node.type == 'transfer':
                continue
                
            code.append(f"% Params for {node.label}")
            for k, v in node.params.items():
                if isinstance(v, bool):
                    v_str = str(v).lower()
                elif isinstance(v, str):
                    v_str = f"'{v}'"
                elif isinstance(v, list):
                    v_str = "{" + ", ".join([f"'{x}'" if isinstance(x, str) else str(x) for x in v]) + "}"
                else:
                    v_str = str(v)
                code.append(f"param.{unique_id}.{k} = {v_str};")
            code.append("")

        code.append("%% GET LIST OF FILES TO PROCESS")
        input_node = next((n for _, n in path_nodes if n.function == 'get_files'), None)
        importer_node = next((n for _, n in path_nodes if n.function in ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']), None)
        
        file_paths = []
        if input_node:
            file_paths = input_node.params.get('file_paths', [])
        elif importer_node:
            if importer_node.function == 'pop_mffimport':
                fname = importer_node.params.get('mffFile', '')
                fpath = ''
            else:
                fname = importer_node.params.get('filename', '')
                fpath = importer_node.params.get('filepath', '')
                
            if fname:
                if fpath:
                    file_paths.append(os.path.join(fpath, fname))
                else:
                    file_paths.append(fname)
            
        code.append("fileList = {")
        for i, fp in enumerate(file_paths):
            folder, name = os.path.split(fp)
            code.append(f"    {i+1}, '{folder}', '{name}', '{fp}';")
        code.append("};")
        code.append("")
        
        code.append("%% RUN PIPELINE")
        code.append("run_pipeline(fileList, param);")
        code.append("")
        
        code.append("%% Processing Function")
        code.append("function run_pipeline(fileList, param)")
        code.append("    for fL = 1:size(fileList, 1)")
        
        stop_on_error = settings.get('stop_on_error', True)
        if not stop_on_error:
            code.append("        try")
            indent = "            "
        else:
            code.append("        % Stop on error is enabled")
            indent = "        "
            
        code.append(indent + "log = struct();")
        code.append(indent + "log.input.file = fileList(fL,:);")
        code.append(indent + "if isempty(fileList); continue; end")
        code.append(indent + "[~, current_fname, ~] = fileparts(fileList{fL,3});")
        code.append(indent + "param.current_filename = current_fname;")
        
        # BIDS Parsing
        code.append(indent + "[param.sub, param.ses, param.task, param.run] = util_parseBIDS(current_fname);")
        
        # Transfer tracking
        transfer_vars = {} # transfer_node_id -> var_name
        for n in self.pipeline.nodes:
            if n.type == 'transfer':
                transfer_vars[n.id] = f"trans_v_{n.id[:8].replace('-', '_')}"
        
        # Extraction points: source_node_id -> list of (var_name, field)
        extraction_points = {}
        for e in self.pipeline.edges:
            if e.target in transfer_vars:
                T_id = e.target
                S_id = e.source
                field = node_map[T_id].params.get('field', 'chanlocs')
                if S_id not in extraction_points:
                    extraction_points[S_id] = []
                extraction_points[S_id].append((transfer_vars[T_id], field))

        importer_funcs = ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']
        
        for unique_id, node in path_nodes:
            if node.function == 'get_files':
                continue
            
            # Injection: Apply any incoming transfers
            for param_name, trans_info in node.transfer_inputs.items():
                T_id = trans_info.get('source_node_id')
                if T_id in transfer_vars:
                    v_name = transfer_vars[T_id]
                    code.append(indent + f"if exist('{v_name}', 'var'); param.{unique_id}.{param_name} = {v_name}; end")
                
            if node.function in importer_funcs:
                code.append(indent + f"[EEG, log] = step_importEEG(fileList{{fL,4}}, param, log, '{node.function}', '{unique_id}');")
            elif node.type == 'visualization':
                code.append(indent + f"log = step_plot(EEG, param.{unique_id}, log, '{node.function}', '{unique_id}', param);")
            else:
                code.append(indent + f"[EEG, log] = step_process(EEG, param.{unique_id}, log, '{node.function}', '{unique_id}', param);")
            
            # Extraction: Save any outgoing transfers
            if node.id in extraction_points:
                for v_name, field in extraction_points[node.id]:
                    code.append(indent + f"if ~isempty(EEG) && isfield(EEG, '{field}'); {v_name} = EEG.{field}; end")
                
        code.append(indent + "util_createReport(param, log);")
        
        if not stop_on_error:
            code.append("        catch ME")
            code.append("            fprintf('Error processing file %s: %s\\n', fileList{fL,3}, ME.message);")
            code.append("            util_createReport(param, log);")
            code.append("        end")
            
        code.append("    end")
        code.append("end")
        code.append("")
        
        code.append(self._get_boilerplate())
        return "\n".join(code)
        
    def _get_boilerplate(self):
        return """
%% Step Functions

function [EEG, log] = step_importEEG(path_raw, param, log, funcName, stepKeyword)
    if ~util_prevStepSuccess(log); EEG=[]; return; end 
    try
        if strcmp(funcName, 'pop_loadset')
            [filepath, name, ext] = fileparts(path_raw);
            EEG = pop_loadset('filename', [name ext], 'filepath', filepath);
        else
            EEG = feval(funcName, path_raw);
        end
        EEG = eeg_checkset(EEG);
        success = 1;
        logKeyPair = {'proc_success', success; 'param_path', path_raw};
    catch ME
        success = 0;
        logKeyPair = {'proc_success', success; 'param_path', path_raw; 'error', ME.message};
    end
    log = util_wrapUpStep(EEG, param, log, stepKeyword, logKeyPair, success);
end

function [EEG, log] = step_process(EEG, stepParam, log, funcName, stepKeyword, param)
    if ~util_prevStepSuccess(log); return; end
    try
        % Handle BIDS-compliant global output folder for pop_saveset
        if strcmp(funcName, 'pop_saveset') && isfield(stepParam, 'use_global_savepath') && stepParam.use_global_savepath
            % Build BIDS Derivatives path: derivatives/DAG/sub-XX/ses-YY/eeg/
            save_path = fullfile(param.path_globalSavepath, 'derivatives', 'DAG', param.sub);
            if ~isempty(param.ses); save_path = fullfile(save_path, param.ses); end
            save_path = fullfile(save_path, 'eeg');
            
            if ~exist(save_path, 'dir'); mkdir(save_path); end
            stepParam.filepath = save_path;
            
            % Build BIDS-compliant filename: sub-01_ses-01_task-rest_desc-preproc_eeg.set
            suffix = 'preproc';
            if isfield(stepParam, 'suffix'); suffix = stepParam.suffix; end % If node has a custom suffix
            
            fname = param.sub;
            if ~isempty(param.ses); fname = [fname '_' param.ses]; end
            if ~isempty(param.task); fname = [fname '_' param.task]; end
            if ~isempty(param.run); fname = [fname '_' param.run]; end
            fname = [fname '_desc-' suffix '_eeg.set'];
            
            stepParam.filename = fname;
        end

        fields = fieldnames(stepParam);
        args = {};
        
        % Only append EEG if it's not a loading function
        isImporter = ismember(funcName, {'pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig'});
        if ~isImporter
            args{end+1} = EEG;
        end
        
        for i=1:length(fields)
            % Skip internal flags
            if strcmp(fields{i}, 'use_global_savepath'); continue; end
            
            val = stepParam.(fields{i});
            if isempty(val); continue; end
            args{end+1} = fields{i};
            args{end+1} = val;
        end
        
        EEG = feval(funcName, args{:});
        if ~isempty(EEG)
            EEG = eeg_checkset(EEG);
        end
        success = 1;
        logKeyPair = {'proc_success', success; 'func', funcName};
    catch ME
        success = 0;
        logKeyPair = {'proc_success', success; 'func', funcName; 'error', ME.message};
    end
    log = util_wrapUpStep(EEG, stepParam, log, stepKeyword, logKeyPair, success);
end

function log = step_plot(EEG, stepParam, log, funcName, stepKeyword, param)
    if ~util_prevStepSuccess(log); return; end
    try
        fields = fieldnames(stepParam);
        args = {EEG};
        
        use_global = isfield(stepParam, 'use_global_savepath') && stepParam.use_global_savepath;
        
        % Resolve save directory and filename separately
        % These are pipeline-managed fields, not native MATLAB function args
        save_dir  = '';
        save_file = '';
        if isfield(stepParam, 'filepath') && ~isempty(stepParam.filepath)
            save_dir = stepParam.filepath;
        end
        if isfield(stepParam, 'filename') && ~isempty(stepParam.filename)
            save_file = stepParam.filename;
        end
        
        % When use_global_savepath is on, build BIDS-aware directory and filename
        if use_global
            % Build BIDS Figures path: derivatives/DAG/sub-XX/ses-YY/figures/
            save_dir = fullfile(param.path_globalSavepath, 'derivatives', 'DAG', param.sub);
            if ~isempty(param.ses); save_dir = fullfile(save_dir, param.ses); end
            save_dir = fullfile(save_dir, 'figures');
            
            if ~exist(save_dir, 'dir'); mkdir(save_dir); end
            
            % Build BIDS-aware filename: sub-01_ses-01_task-rest_desc-topoplot.png
            fname = param.sub;
            if ~isempty(param.ses); fname = [fname '_' param.ses]; end
            if ~isempty(param.task); fname = [fname '_' param.task]; end
            if ~isempty(param.run); fname = [fname '_' param.run]; end
            
            % Use the node label or function name as the plot description
            plot_desc = funcName;
            if isfield(stepParam, 'desc') && ~isempty(stepParam.desc); plot_desc = stepParam.desc; end
            
            save_file = [fname '_desc-' plot_desc '.png'];
        end
        
        for i=1:length(fields)\n
            % Skip pipeline-managed fields — not passed as args to the plot function
            if ismember(fields{i}, {'use_global_savepath', 'filepath', 'filename'}); continue; end
            
            val = stepParam.(fields{i});
            if isempty(val); continue; end
            
            args{end+1} = fields{i};
            args{end+1} = val;
        end

        % Execute the plotting function
        feval(funcName, args{:}); 
        
        % Save figure if a path is defined
        filename = '';
        if ~isempty(save_dir) && ~isempty(save_file)
            if ~exist(save_dir, 'dir'); mkdir(save_dir); end
            fig = gcf;
            filename = fullfile(save_dir, save_file);
            saveas(fig, filename);
            close(fig);
        end
        
        success = 1;
        logKeyPair = {'proc_success', success; 'func', funcName; 'out_savedFigure', filename};

    catch ME
        success = 0;
        logKeyPair = {'proc_success', success; 'func', funcName; 'error', ME.message};
    end
    log = util_wrapUpStep(EEG, struct(), log, stepKeyword, logKeyPair, success);
end

%% Util Functions

function success = util_prevStepSuccess(log)
    if isfield(log, 'stepOrder')
        laststep = log.stepOrder{end};
        success = log.(laststep).proc_success;
    else
        success = 1;
    end
end

function log = util_createLog(log, step, logKeyPair)
    if isfield(log, 'stepOrder')
        log.stepOrder{end+1} = step;
    else
        log.stepOrder = {step};
    end
    for iKey = 1:size(logKeyPair, 1)
        log.(step).(logKeyPair{iKey, 1}) = logKeyPair{iKey, 2};
    end
end

function log = util_wrapUpStep(EEG, param, log, stepName, logKeyPair, success)
    log = util_createLog(log, stepName, logKeyPair);
    if ~isempty(EEG)
        log.(stepName).EEG_trials = EEG.trials;
        log.(stepName).EEG_pnts = EEG.pnts;
    end
end

function [sub, ses, task, run] = util_parseBIDS(fname)
    % Extract sub, ses, task, run from BIDS filename
    sub = ''; ses = ''; task = ''; run = '';
    
    tokens = regexp(fname, 'sub-([a-zA-Z0-9]+)', 'tokens');
    if ~isempty(tokens); sub = ['sub-' tokens{1}{1}]; end
    
    tokens = regexp(fname, 'ses-([a-zA-Z0-9]+)', 'tokens');
    if ~isempty(tokens); ses = ['ses-' tokens{1}{1}]; end
    
    tokens = regexp(fname, 'task-([a-zA-Z0-9]+)', 'tokens');
    if ~isempty(tokens); task = ['task-' tokens{1}{1}]; end
    
    tokens = regexp(fname, 'run-([a-zA-Z0-9]+)', 'tokens');
    if ~isempty(tokens); run = ['run-' tokens{1}{1}]; end
    
    % Fallback if sub is missing
    if isempty(sub)
        sub = 'sub-unknown';
    end
end

function util_createReport(param, log)
    if ~param.openWeb; return; end
    disp('Generating HTML report from log...');
    % Detailed HTML report logic can be expanded here based on pipeline_ICCRN_Jeremy.m
end
"""
