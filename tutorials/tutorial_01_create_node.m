%% Tutorial 1: Creating a Custom Node for EEGLAB-DAG
% Welcome! This tutorial will guide you through creating your own custom
% "node" for the EEGLAB-DAG editor. 
%
% Think of a "node" as a single building block or step in your data processing
% pipeline (like "Load Data", "Filter", or "Run ICA").
%
% Behind the scenes, the DAG Editor uses a format called "JSON" 
% (JavaScript Object Notation) to understand what each node does. 
% Don't let the name intimidate you! JSON is simply a standardized, 
% human-readable way of writing down a list of properties—very similar to 
% a MATLAB "struct" or a basic list of attributes.
%
% By running this MATLAB script, we will define the properties of our new 
% node and save it as a file that the DAG Editor can read and use immediately.

%% Step 1: Define the Basic Information
% First, we create a MATLAB struct to hold our node's information.
node = struct();

% 1. name: This is the human-readable name that will appear on the block 
%    in the DAG Editor canvas.
node.name = 'My Custom Filter';

% 2. function: This is the EXACT name of the MATLAB/EEGLAB function that
%    will be executed when this node runs. We will use a standard EEGLAB 
%    function here as an example.
node.function = 'pop_eegfiltnew';

% 3. type: This tells the editor what kind of ports the node should have.
%    - "process": Has both input and output ports (most common).
%    - "input": Only has an output port (e.g., loading a file).
%    - "output": Only has an input port (e.g., saving a file).
%    - "visualization": Only has an input port (e.g., plotting).
node.type = 'process';

% 4. category: This determines which folder the node will be grouped under
%    in the sidebar menu (e.g., "File", "Edit", "Tools", "Plot").
node.category = 'Tools';

% 5. description: A brief summary of what the node does. This appears
%    when you hover over the node in the editor.
node.description = 'Applies a custom bandpass filter to the data.';

% 6. suffix: This is a short code (e.g. "BP") that will be added to the 
%    original filename when saving the output of this node. As data flows 
%    through multiple nodes, these suffixes accumulate (e.g., NAME_BP_RS).
node.suffix = 'MYF';

%% Step 2: Define the Inputs (Parameters)
% The inputs section defines what data goes into the node, and what 
% settings (parameters) the user can tweak in the sidebar.

% We define this as an array of structs (a list of different inputs).
% The first input for a processing node is almost always the EEG data itself.
input1 = struct();
input1.name = 'EEG';
input1.type = 'dataset'; % Tells the editor this is EEG data flowing through the cables
input1.description = 'Input EEG structure';
input1.required = true;

% The second input might be a parameter, like the low-pass frequency cutoff.
input2 = struct();
input2.name = 'locutoff'; % The exact parameter name expected by the MATLAB function
input2.type = 'float';    % 'float' means a decimal number. Other types include 'integer', 'string', 'bool' (checkbox), etc.
input2.description = 'Low edge of the passband (Hz)';
input2.required = false;  % If false, it's hidden under an "Optional Parameters" menu
input2.default = 1.0;     % The default value shown in the editor

% The third input could be the high-pass frequency cutoff.
input3 = struct();
input3.name = 'hicutoff';
input3.type = 'float';
input3.description = 'High edge of the passband (Hz)';
input3.required = false;
input3.default = 50.0;

% Combine these inputs into a single list and attach it to our node.
node.inputs = {input1, input2, input3};

%% Step 3: Define the Outputs
% The outputs section defines what data comes out of the node.
% For most processing nodes, this is simply the modified EEG dataset.

output1 = struct();
output1.name = 'EEG';
output1.type = 'dataset';
output1.description = 'Output EEG structure';

% Attach the output to our node.
node.outputs = {output1};

%% Step 4: Save the Node File
% Now that we have fully defined our node in MATLAB, we need to convert it
% into the JSON format and save it in the "library/nodes" folder. 
% The DAG Editor reads all files in that folder when it starts.

% Determine the path to the library/nodes directory relative to this script
scriptDir = fileparts(mfilename('fullpath'));
nodesDir = fullfile(scriptDir, '..', 'library', 'nodes');

% Ensure the directory exists
if ~exist(nodesDir, 'dir')
    mkdir(nodesDir);
end

% The filename for our new node
filename = fullfile(nodesDir, 'my_custom_filter.json');

% Convert our MATLAB struct into JSON text formatting
% 'PrettyPrint' makes the text nicely spaced and easy for humans to read
jsonText = jsonencode(node, 'PrettyPrint', true);

% Write the text to a file
fileID = fopen(filename, 'w');
if fileID == -1
    error('Could not open file for writing: %s', filename);
end
fprintf(fileID, '%s', jsonText);
fclose(fileID);

fprintf('\nSuccess! The custom node was created at:\n%s\n', filename);
fprintf('If the DAG Editor is currently open, please close and restart it to see your new node!\n');
