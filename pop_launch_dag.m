% pop_launch_dag - Launches the Python-based DAG Pipeline Editor.
%
% Usage:
%   pop_launch_dag();

function pop_launch_dag()
    
    % Determine the path to the plugin directory
    plugin_path = fileparts(which('eegplugin_eeglab_dag'));
    
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
            
            % macOS requires the 'open' command for .app bundles
            command = sprintf('open "%s"', bin_path);
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
