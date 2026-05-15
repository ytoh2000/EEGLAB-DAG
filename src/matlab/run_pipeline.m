% RUN_PIPELINE - Executes an EEGLAB pipeline defined in a JSON job file.
%
% Usage:
%   run_pipeline(job_file)
%
% Input:
%   job_file - Path to the JSON file exported by EEGLAB-DAG.
%
% Description:
%   This script reads the JSON job file, launches EEGLAB, and iterates through
%   the list of files specified in the job. For each file, it applies the
%   sequence of processing steps defined in the 'steps' field.
%
%   Supported steps must correspond to EEGLAB functions (e.g., pop_loadset, 
%   pop_runica) that take an EEG structure as the first input and return it
%   as the first output.
%
% Example:
%   run_pipeline('pipeline_job.json');

function run_pipeline(job_file)

    % Check inputs
    if nargin < 1
        [filename, pathname] = uigetfile('*.json', 'Select Job File');
        if isequal(filename,0)
            disp('User selected Cancel');
            return;
        end
        job_file = fullfile(pathname, filename);
    end

    % 1. Read and Decode JSON
    if ~exist(job_file, 'file')
        error('Job file not found: %s', job_file);
    end
    
    fid = fopen(job_file);
    raw_json = fread(fid, inf);
    str_json = char(raw_json');
    fclose(fid);
    
    raw_job = jsondecode(str_json);
    
    % Support unified format or legacy format
    if isfield(raw_job, 'execution_job')
        if isempty(raw_job.execution_job)
            error('This pipeline is incomplete and cannot be executed. Please fix errors in the DAG Editor.');
        end
        job = raw_job.execution_job;
        
        if isfield(raw_job, 'visual_graph') && isfield(raw_job.visual_graph, 'settings')
            settings = raw_job.visual_graph.settings;
        else
            settings = struct();
        end
    else
        job = raw_job;
        if isfield(job, 'settings')
            settings = job.settings;
        else
            settings = struct();
        end
    end
    
    % Validate job structure
    if ~isfield(job, 'files') || ~isfield(job, 'steps')
        error('Invalid job file format. Must contain "files" and "steps".');
    end

    % 2. Initialize EEGLAB
    if ~exist('eeglab', 'file')
        error('EEGLAB not found in path.');
    end
    eeglab nogui;
    
    % 3. Extract Settings
    % 'settings' was already populated above during parsing
    
    % 4. Initialize Settings & Change Directory
    error_strategy = 'halt';
    if isfield(settings, 'error_strategy')
        error_strategy = settings.error_strategy;
    end
    
    test_mode = false;
    if isfield(settings, 'test_mode')
        test_mode = settings.test_mode;
    end
    
    % If a global save path is provided, try to CD to it
    % This helps resolve relative paths on mapped network drives (e.g. Z:)
    if isfield(settings, 'global_savepath') && ~isempty(settings.global_savepath)
        gpath = settings.global_savepath;
        try
            if ispc
                % On Windows, handle potential drive letter change
                if length(gpath) >= 2 && gpath(2) == ':'
                    drive = gpath(1:2);
                    % Check if drive exists before CD
                    if exist(drive, 'dir')
                        cd(drive);
                        fprintf('  -> Changed current drive to %s\n', drive);
                    end
                end
            end
            
            if exist(gpath, 'dir')
                cd(gpath);
                fprintf('  -> Changed current directory to %s\n', gpath);
            else
                % Try creating it if it doesn't exist
                [ok, msg] = mkdir(gpath);
                if ok
                    cd(gpath);
                    fprintf('  -> Created and changed directory to %s\n', gpath);
                end
            end
        catch ME
            fprintf('  -> Warning: Could not change directory to %s: %s\n', gpath, ME.message);
        end
    end
    
    test_sample_size = 1;
    if isfield(settings, 'test_sample_size')
        test_sample_size = settings.test_sample_size;
    end
    
    parallel_processing = false;
    if isfield(settings, 'parallel_processing')
        parallel_processing = settings.parallel_processing;
    end

    % 4. Iterate over files
    input_files = job.files;
    
    if test_mode && length(input_files) > test_sample_size
        fprintf('\n[TEST MODE ENABLED] Randomly sampling %d files out of %d.\n', test_sample_size, length(input_files));
        rng('shuffle');
        idx = randperm(length(input_files), test_sample_size);
        input_files = input_files(idx);
    end
    
    num_files = length(input_files);
    fprintf('Found %d files to process.\n', num_files);
    
    if parallel_processing
        fprintf('Starting parallel processing (requires Parallel Computing Toolbox)...\n');
        parfor i = 1:num_files
            fprintf('\nProcessing file %d/%d: %s (Worker)\n', i, num_files, input_files{i});
            try
                process_single_file(input_files{i}, job.steps);
            catch ME
                if strcmp(error_strategy, 'skip')
                    fprintf('  [SKIPPED] Failed to process file: %s\n  Error: %s\n', input_files{i}, ME.message);
                else
                    fprintf('  [HALTED] Failed to process file: %s\n  Error: %s\n', input_files{i}, ME.message);
                    rethrow(ME);
                end
            end
        end
    else
        for i = 1:num_files
            fprintf('\nProcessing file %d/%d: %s\n', i, num_files, input_files{i});
            try
                process_single_file(input_files{i}, job.steps);
            catch ME
                if strcmp(error_strategy, 'skip')
                    fprintf('  [SKIPPED] Failed to process file: %s\n  Error: %s\n', input_files{i}, ME.message);
                else
                    fprintf('  [HALTED] Failed to process file: %s\n  Error: %s\n', input_files{i}, ME.message);
                    rethrow(ME);
                end
            end
        end
    end
    
    fprintf('\nJob completed.\n');

end

function file_path = util_normalize_path(file_path)
    % Fix mixed slashes and redundant separators
    file_path = strrep(file_path, '\', '/');
    file_path = regexprep(file_path, '/+', '/');
    
    if ispc
        % On Windows, fix Mac-style /Volumes/ paths
        if startsWith(file_path, '/Volumes/')
            parts = strsplit(file_path, '/');
            if length(parts) >= 4
                % Strategy: Strip /Volumes/VolumeName/ and try absolute on current drive root
                % or try relative to PWD.
                rel_path = strjoin(parts(4:end), '\');
                
                % 1. Try relative to current directory
                if exist(rel_path, 'file')
                    file_path = rel_path;
                    return;
                end
                
                % 2. Try at the root of the current drive (common for mapped drives)
                root_path = ['\' rel_path];
                if exist(root_path, 'file')
                    file_path = root_path;
                    return;
                end
                
                % 3. Brute force: check common mapped drive letters
                drives = 'ZYXWVUTSRQPONMLKJIHGFEDC';
                for i = 1:length(drives)
                    drive_path = [drives(i) ':\' rel_path];
                    if exist(drive_path, 'file')
                        file_path = drive_path;
                        return;
                    end
                end
                
                % 4. Fallback: just return the relative path from the root
                file_path = root_path;
            end
        end
        % Final Windows normalization
        file_path = strrep(file_path, '/', '\');
    else
        % Final Unix normalization
        file_path = strrep(file_path, '\', '/');
    end
end

function process_single_file(file_path, steps)
    file_path = util_normalize_path(file_path);
    

    [~, fname, fext] = fileparts(file_path);
    current_EEG = []; 
    transfers = struct(); % Store transferred subfields (e.g. chanlocs)
    for s = 1:length(steps)
        if iscell(steps)
            step = steps{s};
        else
            step = steps(s);
        end
        func_name = step.function;
        params = step.parameters;
        
        fprintf('  -> Step %d: %s (%s)\n', s, func_name, step.label);
        
        args = {};
        importer_funcs = {'pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig'};
        is_importer = ismember(func_name, importer_funcs);
        
        if ~is_importer
           if isempty(current_EEG)
               error('Attempting to process %s but no EEG data loaded yet.', func_name);
           end
           args{end+1} = current_EEG;
        end
        
        if is_importer && s == 1
            if strcmp(func_name, 'pop_loadset')
                 args{end+1} = 'filename';
                 args{end+1} = [fname fext];
                 args{end+1} = 'filepath';
                 args{end+1} = fileparts(file_path);
            elseif any(strcmp(func_name, {'pop_mffimport', 'pop_fileio', 'pop_biosig'}))
                 args{end+1} = file_path;
            end
        end

        if strcmp(func_name, 'pop_saveset')
            if ~isfield(params, 'filename') || isempty(params.filename)
                args{end+1} = 'filename';
                if isfield(step, 'current_suffix')
                    args{end+1} = [fname step.current_suffix fext];
                else
                    args{end+1} = [fname fext];
                end
            end
        end
        
        % Injection: Apply any incoming transfers
        if isfield(step, 'transfer_in')
            tin = step.transfer_in;
            if isstruct(tin)
                for t = 1:length(tin)
                    t_info = tin(t);
                    if isfield(transfers, t_info.var_name)
                        params.(t_info.param) = transfers.(t_info.var_name);
                    end
                end
            end
        end
        
        mapped_args = {};
        if isfield(step, 'arguments')
            step_args = step.arguments;
            if ~isempty(step_args)
                if ~iscell(step_args)
                    step_args = num2cell(step_args);
                end
                mapped_args = step_args(:)';
            end
        else
            param_names = fieldnames(params);
            for p = 1:length(param_names)
                pname = param_names{p};
                pval = params.(pname);
                
                if isempty(pval) || (ischar(pval) && strcmp(pval, 'off'))
                    continue;
                end
                
                if is_importer && s == 1
                    if strcmp(func_name, 'pop_loadset') && (strcmp(pname, 'filename') || strcmp(pname, 'filepath'))
                        continue;
                    elseif strcmp(func_name, 'pop_mffimport') && strcmp(pname, 'mffFile')
                        continue;
                    elseif any(strcmp(func_name, {'pop_fileio', 'pop_biosig'})) && strcmp(pname, 'filename')
                        continue;
                    end
                end
                
                if iscell(pval) && iscellstr(pval)
                     % keep
                elseif ischar(pval)
                     % keep
                end
                
                % Auto-parse potential lists for channel/index parameters
                list_params = {'rmchannel', 'channel', 'badchans', 'chanind', 'exclude', 'ref', 'components', 'electrodes', 'icacomps'};
                if ismember(pname, list_params)
                    pval = util_parse_list(pval);
                end
                
                mapped_args{end+1} = pname;
                mapped_args{end+1} = pval;
            end
        end
        args = [args, mapped_args];
        
        try
            current_EEG = feval(func_name, args{:});
            
            if isempty(current_EEG)
                 error('Function %s returned empty result.', func_name);
            end
            
            current_EEG = eeg_checkset(current_EEG);
            
            % Extraction: Save any outgoing transfers
            if isfield(step, 'transfer_out')
                tout = step.transfer_out;
                if isstruct(tout)
                    for t = 1:length(tout)
                        t_info = tout(t);
                        if isfield(current_EEG, t_info.field)
                            transfers.(t_info.var_name) = current_EEG.(t_info.field);
                        end
                    end
                end
            end
            
            if isfield(step, 'save_at_this_step') && step.save_at_this_step
                suffix = step.current_suffix;
                save_name = [fname suffix fext];
                fprintf('    (Automatic Save: %s)\n', save_name);
                pop_saveset(current_EEG, 'filename', save_name, 'filepath', fileparts(file_path));
            end                    
        catch ME
            warning('Error executing %s: %s', func_name, ME.message);
            rethrow(ME);
        end
    end
end

function val = util_parse_list(val)
    % Parses a space/comma separated string into a numeric array or cell array of strings.
    if ~ischar(val) || isempty(val)
        return;
    end
    
    val = strtrim(val);
    
    % Strip brackets if present
    if startsWith(val, '[') && endsWith(val, ']')
        val = strtrim(val(2:end-1));
    end
    
    % Strip quotes if they wrap the whole thing
    if (startsWith(val, "'") && endsWith(val, "'")) || (startsWith(val, '"') && endsWith(val, '"'))
        val = val(2:end-1);
    end
    
    if isempty(val)
        val = [];
        return;
    end
    
    % Split by spaces or commas
    parts = strsplit(val, {',', ' '});
    parts = parts(~cellfun(@isempty, parts));
    
    if isempty(parts)
        val = [];
        return;
    end
    
    % Check if all parts are numbers
    all_num = true;
    nums = zeros(1, length(parts));
    for i = 1:length(parts)
        p = parts{i};
        % Strip quotes from individual parts if present
        if (startsWith(p, "'") && endsWith(p, "'")) || (startsWith(p, '"') && endsWith(p, '"'))
            p = p(2:end-1);
            parts{i} = p;
        end
        
        n = str2double(p);
        if isnan(n)
            all_num = false;
        else
            nums(i) = n;
        end
    end
    
    if all_num
        val = nums;
    else
        val = parts;
    end
end
