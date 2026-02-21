% eegplugin_eeglab_dag - EEGLAB plugin for the DAG Pipeline Editor.
%
% Usage:
%   eegplugin_eeglab_dag(fig, try_strings, catch_strings);
%
% Inputs:
%   fig            - [integer] EEGLAB figure handle
%   try_strings    - [struct] EEGLAB "try" strings
%   catch_strings  - [struct] EEGLAB "catch" strings

function eegplugin_eeglab_dag(fig, try_strings, catch_strings)

    % Add src/matlab to path so run_pipeline can be found
    plugin_path = fileparts(which('eegplugin_eeglab_dag'));
    addpath(fullfile(plugin_path, 'src', 'matlab'));

    % Create top-level menu 'DAG'
    % This will appear in the main EEGLAB menu bar.
    menu = uimenu(fig, 'Label', 'DAG');

    % Menu Item 1: DAG editor
    % Calls pop_launch_dag()
    uimenu(menu, 'Label', 'DAG editor', ...
        'Callback', 'pop_launch_dag();');

    % Menu Item 2: Execute Job
    % Calls run_pipeline()
    uimenu(menu, 'Label', 'Execute Job', ...
        'Callback', 'run_pipeline();');
        
end
