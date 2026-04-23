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
    
    job = jsondecode(str_json);
    
    % Validate job structure
    if ~isfield(job, 'files') || ~isfield(job, 'steps')
        error('Invalid job file format. Must contain "files" and "steps".');
    end

    % 2. Initialize EEGLAB
    if ~exist('eeglab', 'file')
        error('EEGLAB not found in path.');
    end
    eeglab nogui;
    
    % 3. Iterate over files
    num_files = length(job.files);
    fprintf('Found %d files to process.\n', num_files);
    
    for i = 1:num_files
        file_path = job.files{i};
        [~, fname, fext] = fileparts(file_path);
        
        fprintf('\nProcessing file %d/%d: %s\n', i, num_files, fname);
        
        try
            % 4. Load Data (Implicit first step or Explicit?)
            % If the first step is NOT pop_loadset, we generally need to load it.
            % But typically the pipeline construction implies the source node does loading?
            % In our DAG, 'Get Files' just passes the path. The standard is to then call pop_loadset.
            % However, our DAG *library* defines 'pop_loadset' as a step.
            % If the user put 'Get Files' -> 'Load Set' -> 'Filter', then we follow steps.
            % BUT: 'Get Files' output is a list. The loop is happening HERE.
            % So the first step in the `job.steps` list should normally be the loading function.
            % Let's verify compatibility: pop_loadset takes 'filename', 'filepath'.
            % We might need to inject these params if the first step is a loader.
            
            % Initialize EEG structure (empty) to pass to first function if needed?
            % Most pop_ functions expect (EEG, ...). pop_loadset does not require EEG input usually.
            
            current_EEG = []; # Placeholder
            
            for s = 1:length(job.steps)
                step = job.steps(s);
                func_name = step.function;
                params = step.parameters;
                
                fprintf('  -> Step %d: %s (%s)\n', s, func_name, step.label);
                
                % Prepare Arguments
                % We need to convert the struct 'params' into Name-Value pairs or positional args depending on function.
                % Most pop_ functions support Name-Value pairs or old style positional.
                % Ideally we use the new python library calling style which is often struct or NV pairs.
                % For standard pop_ functions, we can construct the argument list dynamically.
                
                % Special Handling: Input EEG
                % Most functions take EEG as first argument.
                % EXCEPTions: importers (pop_loadset, pop_mffimport, pop_fileio, pop_biosig)
                
                args = {};
                
                % Check if this is an importer (doesn't take EEG as input)
                importer_funcs = {'pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig'};
                is_importer = ismember(func_name, importer_funcs);
                
                if ~is_importer
                   if isempty(current_EEG)
                       error('Attempting to process %s but no EEG data loaded yet.', func_name);
                   end
                   args{end+1} = current_EEG;
                end
                
                % Inject filename/filepath into importer if it's the first step
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

                % Special Handling: pop_saveset
                % If filename is missing, use original filename + accumulated suffix
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
                % Append other parameters from JSON
                param_names = fieldnames(params);
                for p = 1:length(param_names)
                    pname = param_names{p};
                    pval = params.(pname);
                    
                    % Skip internal/empty params if needed, or translate
                    if isempty(pval) || strcmp(pval, 'off')
                        continue;
                    end
                    
                    % Example: Handle 'channels' which might be cell array of strings
                    if iscell(pval) && iscellstr(pval)
                         % keep as cell
                    elseif ischar(pval)
                         % keep as char
                    end
                    
                    args{end+1} = pname;
                    args{end+1} = pval;
                end
                
                % Execute Function
                try
                    if is_importer
                        current_EEG = feval(func_name, args{:});
                    else
                        current_EEG = feval(func_name, args{:});
                    end
                    
                    % Check result
                    if isempty(current_EEG)
                         error('Function %s returned empty result.', func_name);
                    end
                    
                    % Update comments/history if needed
                    current_EEG = eeg_checkset(current_EEG);
                    
                    % Intermediate Save if requested
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
            
            % Done processing file.
            % Note: If the pipeline didn't include a 'pop_saveset', results are lost.
            % The validation in Python should warn about this.
            
        catch ME
            fprintf('  Failed to process file: %s\n  Error: %s\n', fname, ME.message);
        end
    end
    
    fprintf('\nJob completed.\n');

end
