% pop_launch_dag - Launches the Python-based DAG Pipeline Editor.
%
% Usage:
%   pop_launch_dag();

function pop_launch_dag()
    
    % Determine the path to the plugin/app directory
    plugin_path = fileparts(mfilename('fullpath'));
    
    % 1. Try to find bundled executable (compiled with PyInstaller)
    if ispc
        bin_path = fullfile(plugin_path, 'bin', 'win64', 'main', 'main.exe');
    elseif ismac
        % PyInstaller creates a .app bundle on macOS
        bin_path = fullfile(plugin_path, 'bin', 'maca64', 'main.app');
    elseif isunix
        bin_path = fullfile(plugin_path, 'bin', 'linux64', 'main', 'main');
    else
        bin_path = '';
    end

    if exist(bin_path, 'file') || exist(bin_path, 'dir')
        % Found bundled binary!
        if ismac
            % Auto-fix permissions inside the macOS .app bundle
            exec_file = fullfile(bin_path, 'Contents', 'MacOS', 'main');
            system(sprintf('chmod +x "%s"', exec_file));
            
            % Automatically clear Apple's download quarantine flag 
            system(sprintf('xattr -cr "%s"', bin_path));
            
            % Forcefully re-sign the app locally for Apple Silicon (M1/M2/M3)
            system(sprintf('codesign --force --deep -s - "%s"', bin_path));
            
            % macOS requires the 'open' command for .app bundles
            command = sprintf('open "%s"', bin_path);
        elseif ispc
            % Check if we are on a network drive or non-local drive
            is_local = startsWith(bin_path, 'C:', 'IgnoreCase', true);
            if ~is_local
                fprintf('Network/Non-local drive detected. Mirroring to local temp folder for stability...\n');
                
                % Create a local cache directory in the user's temp folder
                local_root = fullfile(tempdir, 'EEGLAB-DAG-Cache');
                if ~exist(local_root, 'dir'); mkdir(local_root); end
                
                % Use a subfolder named after the parent directory structure to avoid collisions
                [bin_dir, bin_name, bin_ext] = fileparts(bin_path);
                
                % Extract a unique hash or name from the path to ensure separate caches
                % for different versions or locations
                % Extract a unique hash or name from the path to ensure separate caches
                % for different versions or locations
                path_hash = sprintf('%x', sum(double(bin_dir)));
                local_dir = fullfile(local_root, path_hash);
                
                % Mirror the critical folders (bin and library) to local cache
                % This ensures that relative paths like ../../../library/nodes work
                folders_to_copy = {'bin', 'library'};
                success_count = 0;
                
                for f = 1:length(folders_to_copy)
                    src_f = fullfile(plugin_path, folders_to_copy{f});
                    dst_f = fullfile(local_dir, folders_to_copy{f});
                    
                    if exist(src_f, 'dir')
                        % Use xcopy /D /S /I /Y to only copy newer files
                        copy_cmd = sprintf('xcopy /D /S /I /Y "%s" "%s"', src_f, dst_f);
                        [status, ~] = system(copy_cmd);
                        if status == 0
                            success_count = success_count + 1;
                        end
                    end
                end
                
                if success_count == length(folders_to_copy)
                    fprintf('Mirroring complete. Launching from local cache.\n');
                    % Update bin_path and bin_dir to point to the local copy
                    [~, bin_name, bin_ext] = fileparts(bin_path);
                    % Original bin_path was plugin_path/bin/win64/main/main.exe
                    % New bin_path should be local_dir/bin/win64/main/main.exe
                    bin_path = fullfile(local_dir, 'bin', 'win64', 'main', [bin_name bin_ext]);
                else
                    fprintf('Mirroring partially failed. Attempting to launch from original location...\n');
                end
            end
            
            [bin_dir, bin_name, bin_ext] = fileparts(bin_path);
            command = sprintf('cd /d "%s" && start "" "%s%s"', bin_dir, bin_name, bin_ext);
        else
            command = sprintf('"%s" &', bin_path);
        end
        
        fprintf('Launching DAG Editor (Bundled)...\n');
        fprintf('Command: %s\n', command);
        system(command);
        return;
    end



    % 2. Fallback: Try to find the virtual environment in the plugin folder
    % (Useful for development or if binary is missing)
    venv_python = fullfile(plugin_path, '.venv', 'bin', 'python');
    if ispc
        venv_python = fullfile(plugin_path, '.venv', 'Scripts', 'python.exe');
    end
    
    if exist(venv_python, 'file')
        python_exec = venv_python;
    else
        % 3. Fallback to system python (hope it has dependencies)
        % Check if 'python3' is available
        [status, cmdout] = system('which python3');
        if status == 0
            python_exec = strtrim(cmdout);
        else
            python_exec = 'python';
        end
        
        warning('DAG:VenvNotFound', ...
            'Virtual environment not found in %s. Using system python: %s', ...
            plugin_path, python_exec);
    end
    
    % Path to main.py
    main_script = fullfile(plugin_path, 'src', 'main.py');
    
    % Construct command
    % Check if we need to quote paths
    command = sprintf('"%s" "%s" &', python_exec, main_script);
    
    fprintf('Launching DAG Editor (Python)...\n');
    fprintf('Command: %s\n', command);
    
    % Execute system command in background
    system(command);
    
end
