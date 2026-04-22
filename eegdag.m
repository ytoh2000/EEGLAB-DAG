% eegdag - Launches the standalone DAG Pipeline Editor.
%
% Usage:
%   eegdag();

function eegdag()
    % Determine the path to the app directory
    app_path = fileparts(mfilename('fullpath'));
    
    % Add the src/matlab folder to the MATLAB path so the Python GUI 
    % can communicate with MATLAB functions (like run_pipeline)
    addpath(fullfile(app_path, 'src', 'matlab'));
    
    % Launch the Python-based DAG Editor
    pop_launch_dag();
end
