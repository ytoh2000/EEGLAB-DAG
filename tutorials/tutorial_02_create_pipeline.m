%% Tutorial 2: Creating a Pipeline Programmatically
% Welcome! In this tutorial, we will learn how to build an entire processing 
% pipeline using MATLAB code, without needing to drag and drop in the 
% DAG Editor interface.
% 
% Why do this? If you need to generate many similar pipelines automatically, 
% or share a specific configuration as a script, building it programmatically 
% can save a lot of time.
%
% Just like nodes, pipelines are saved as "JSON" files. A pipeline JSON simply
% lists which nodes are on the canvas, where they are placed (their X/Y
% coordinates), and how they are connected to each other via cables (edges).

%% Step 1: Initialize the Pipeline Structure
% We start by creating an empty struct to hold our pipeline data.
% A pipeline requires two main lists: 'nodes' and 'edges'.
pipeline = struct();
pipeline.nodes = {};
pipeline.edges = {};

%% Step 2: Define the Nodes
% Now, let's add some nodes to our pipeline. We will create a simple 
% 3-step pipeline: Load Data -> Filter -> Clean Data.

% --- Node 1: Load Data ---
% Each node in the pipeline must have a unique ID (like "1", "2", "3").
node1 = struct();
node1.id = '1';
node1.type = 'input';           % This is a source node
node1.function = 'get_files';   % The function defined in the node JSON
node1.label = 'Get File(s)';    % The label shown on the canvas
node1.position = [50, 100];     % [X, Y] coordinates on the canvas screen
node1.parameters = struct();    
node1.parameters.file_paths = {}; % We leave it empty; the user can fill it in the GUI

% --- Node 2: Filter ---
node2 = struct();
node2.id = '2';
node2.type = 'process';
node2.function = 'pop_eegfiltnew';
node2.label = 'FIR Filter';
node2.position = [250, 100];    % Placed further to the right (X = 250)
% We can set specific parameter values right here!
node2.parameters = struct();
node2.parameters.locutoff = '1';
node2.parameters.hicutoff = '50';
% We can also choose to save the output of this specific step!
node2.save_output = true; 

% --- Node 3: Clean Data ---
node3 = struct();
node3.id = '3';
node3.type = 'process';
node3.function = 'pop_clean_rawdata';
node3.label = 'Clean Raw Data';
node3.position = [450, 100];    % Even further right (X = 450)
node3.parameters = struct();

% Add our three nodes to the pipeline's node list.
pipeline.nodes = {node1, node2, node3};

%% Step 3: Define the Edges (Connections)
% Nodes don't do anything unless data flows between them. We create "edges" 
% (the cables on the screen) to connect the output of one node to the input of another.

% Edge 1 connects Node 1 (Load) to Node 2 (Filter)
edge1 = struct();
edge1.source = '1'; % The ID of the node sending the data
edge1.target = '2'; % The ID of the node receiving the data

% Edge 2 connects Node 2 (Filter) to Node 3 (Clean)
edge2 = struct();
edge2.source = '2';
edge2.target = '3';

% Add the edges to the pipeline's edge list.
pipeline.edges = {edge1, edge2};

%% Step 4: Save the Pipeline File
% Our pipeline is complete! We will now convert our MATLAB struct into a 
% JSON file and save it in the "library/pipelines" folder.

% Determine the path to the library/pipelines directory
scriptDir = fileparts(mfilename('fullpath'));
pipelinesDir = fullfile(scriptDir, '..', 'library', 'pipelines');

% Ensure the directory exists
if ~exist(pipelinesDir, 'dir')
    mkdir(pipelinesDir);
end

% The filename for our new pipeline
filename = fullfile(pipelinesDir, 'my_tutorial_pipeline.json');

% Convert to nicely formatted JSON text
jsonText = jsonencode(pipeline, 'PrettyPrint', true);

% Write to file
fileID = fopen(filename, 'w');
if fileID == -1
    error('Could not open file for writing: %s', filename);
end
fprintf(fileID, '%s', jsonText);
fclose(fileID);

fprintf('\nSuccess! The tutorial pipeline was created at:\n%s\n', filename);
fprintf('You can now open the DAG Editor and click the "Load" button to open this pipeline!\n');
