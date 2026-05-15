% pop_launch_dag - Launches the Python-based DAG Pipeline Editor.
%
% Usage:
%   pop_launch_dag();

function pop_launch_dag(force_python)
    if nargin < 1, force_python = 0; end
    
    % Determine the path to the plugin/app directory
    plugin_path = fileparts(mfilename('fullpath'));
    
    % Check if we are on a Windows network drive (common cause of PyInstaller PKG errors)
    if ispc && ~force_python && ~startsWith(plugin_path, 'C:', 'IgnoreCase', true)
         res = questdlg({['The DAG plugin is located on a network drive (', plugin_path(1:2), ').'], ...
             'This often causes "Could not load PKG archive" errors with the bundled binary.', ...
             '', 'Would you like to try launching via Python instead?'}, ...
             'Network Drive Detected', 'Use Python', 'Try Binary anyway', 'Cancel', 'Use Python');
         
         if strcmp(res, 'Use Python')
             force_python = 1; 
         elseif strcmp(res, 'Cancel')
             return;
         end
    end

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

    if ~force_python && (exist(bin_path, 'file') || exist(bin_path, 'dir'))
        % Found bundled binary!
        if ismac
            % Auto-fix permissions inside the macOS .app bundle
            exec_file = fullfile(bin_path, 'Contents', 'MacOS', 'main');
            system(sprintf('chmod +x "%s"', exec_file));
            system(sprintf('xattr -cr "%s"', bin_path));
            system(sprintf('codesign --force --deep -s - "%s"', bin_path));
            command = sprintf('open "%s"', bin_path);
        elseif ispc
            % On Windows, CD into the directory first to help PyInstaller find its 
            % PKG archive and DLLs, especially on network drives or long paths.
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
    venv_python = fullfile(plugin_path, '.venv', 'bin', 'python');
    if ispc
        venv_python = fullfile(plugin_path, '.venv', 'Scripts', 'python.exe');
    end
    
    if exist(venv_python, 'file')
        python_exec = venv_python;
    else
        % 3. Fallback to system python
        [status, cmdout] = system('which python3');
        if status == 0
            python_exec = strtrim(cmdout);
        else
            python_exec = 'python';
        end
        
        if ~force_python
            warning('DAG:VenvNotFound', ...
                'Virtual environment not found in %s. Using system python: %s', ...
                plugin_path, python_exec);
        end
    end
    
    % Path to main.py
    main_script = fullfile(plugin_path, 'src', 'main.py');
    
    % Construct command
    command = sprintf('"%s" "%s" &', python_exec, main_script);
    
    fprintf('Launching DAG Editor (Python)...\n');
    fprintf('Command: %s\n', command);
    system(command);
end
