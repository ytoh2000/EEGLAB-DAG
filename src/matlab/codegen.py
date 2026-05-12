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
        sources = [n for n in G.nodes if G.in_degree(n) == 0]
        end_nodes = [n for n in G.nodes if G.out_degree(n) == 0]
        if not end_nodes:
            end_nodes = list(G.nodes) # fallback
            
        all_paths = []
        for src in sources:
            for end in end_nodes:
                if nx.has_path(G, src, end):
                    paths = list(nx.all_simple_paths(G, src, end))
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
        code.append(f"param.path_outFolder = '{settings.get('output_folder', '')}';")
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
            
            if node.type == 'input':
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
        
        importer_funcs = ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']
        
        for unique_id, node in path_nodes:
            if node.function == 'get_files':
                continue
                
            if node.function in importer_funcs:
                code.append(indent + f"[EEG, log] = step_importEEG(fileList{{fL,4}}, param, log, '{node.function}', '{unique_id}');")
            elif node.type == 'visualization':
                code.append(indent + f"log = step_plot(EEG, param, log, '{node.function}', '{unique_id}');")
            else:
                code.append(indent + f"[EEG, log] = step_process(EEG, param.{unique_id}, log, '{node.function}', '{unique_id}');")
                
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

function [EEG, log] = step_process(EEG, stepParam, log, funcName, stepKeyword)
    if ~util_prevStepSuccess(log); return; end
    try
        fields = fieldnames(stepParam);
        args = {};
        
        % Only append EEG if it's not a loading function
        isImporter = ismember(funcName, {'pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig'});
        if ~isImporter
            args{end+1} = EEG;
        end
        
        for i=1:length(fields)
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

function log = step_plot(EEG, param, log, funcName, stepKeyword)
    if ~util_prevStepSuccess(log); return; end
    try
        % Execute plotting function. Assume custom plotting nodes take (EEG)
        feval(funcName, EEG); 
        
        % Save the figure to report/plot/PLOT_SPECIFIC_FOLDER_NAME/plot_name.jpg
        figPath = fullfile(param.path_outFolder, 'report', 'plot', param.current_filename);
        if ~exist(figPath, 'dir'); mkdir(figPath); end
        
        fig = gcf;
        filename = fullfile(figPath, [stepKeyword '.jpg']);
        saveas(fig, filename);
        close(fig);
        
        success = 1;
        logKeyPair = {'proc_success', success; 'func', funcName; 'out_savedFigures', {filename}};
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
end

function util_createReport(param, log)
    if ~param.openWeb; return; end
    disp('Generating HTML report from log...');
    % Detailed HTML report logic can be expanded here based on pipeline_ICCRN_Jeremy.m
end
"""
