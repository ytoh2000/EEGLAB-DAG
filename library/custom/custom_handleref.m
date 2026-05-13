% CUSTOM_HANDLEREF - Add or remove the reference channel from an EEG dataset
%
% Usage:
%   >> [EEG, action] = custom_handleref(EEG, 'key', 'val');
%
% Inputs:
%   EEG        - Input EEGLAB EEG structure
%
% Optional inputs:
%   'ref'      - [string] Label of the reference channel (e.g. 'Cz').
%                {default: 'Cz'}
%   'action'   - ['auto'|'add'|'remove'] Action to perform.
%                'auto'   - If the channel exists, remove it; if missing,
%                           add a zero-filled channel at the end. (default)
%                'add'    - Add a zero-filled reference channel. Errors if
%                           the channel already exists.
%                'remove' - Remove the reference channel. Errors if the
%                           channel is not found.
%   'locfile'  - [string] Path to a channel location file (.ced, .sfp,
%                .elp, .xyz, .loc) used as a fallback when the channel
%                cannot be found in EEG.urchanlocs. {default: ''}
%
% Outputs:
%   EEG        - Output EEGLAB EEG structure
%   action     - [string] Action that was performed: 'added' or 'removed'
%
% Notes:
%   When adding a reference channel, a row of zeros is appended to the
%   data matrix. This is appropriate for data that has already been
%   re-referenced (e.g. average reference), where the original reference
%   electrode carries a flat signal by definition.
%
%   Coordinate lookup priority (when adding):
%     1. EEG.urchanlocs - original channel locations preserved by EEGLAB.
%        These are guaranteed to match the dataset's coordinate system.
%     2. locfile - external channel location file (fallback). Warning:
%        nose direction and coordinate conventions may differ.
%     3. Label only - if neither source is available, the channel is added
%        with no coordinates.
%
% Examples:
%   % Auto mode: remove Cz if present, or add it back if missing
%   EEG = custom_handleref(EEG, 'ref', 'Cz');
%
%   % Add Cz back (coordinates looked up from EEG.urchanlocs automatically)
%   EEG = custom_handleref(EEG, 'ref', 'Cz', 'action', 'add');
%
%   % Add Cz back with fallback to a location file
%   EEG = custom_handleref(EEG, 'ref', 'Cz', 'action', 'add', ...
%                          'locfile', '/path/to/chanlocs.ced');
%
%   % Remove the reference channel
%   EEG = custom_handleref(EEG, 'ref', 'Cz', 'action', 'remove');
%
% Author: Yong Oh, 2025

% Copyright (C) Yong Oh
%
% Redistribution and use in source and binary forms, with or without
% modification, are permitted provided that the following conditions are met:
%
% 1. Redistributions of source code must retain the above copyright notice,
%    this list of conditions and the following disclaimer.
%
% 2. Redistributions in binary form must reproduce the above copyright notice,
%    this list of conditions and the following disclaimer in the documentation
%    and/or other materials provided with the distribution.
%
% THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
% AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
% IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
% ARE DISCLAIMED.

function [EEG, action, com] = custom_handleref(EEG, varargin)

    com = '';
    action = '';

    if nargin < 1
        help custom_handleref;
        return;
    end

    % Parse inputs
    opt = finputcheck(varargin, { ...
        'ref'      'string'   []        'Cz'; ...
        'action'   'string'   {'auto','add','remove'}  'auto'; ...
        'locfile'  'string'   []        '' ...
    }, 'custom_handleref');
    if ischar(opt), error(opt); end

    % Find the reference channel in the current dataset
    refInd = find(strcmpi({EEG.chanlocs.labels}, opt.ref));

    switch lower(opt.action)
        case 'auto'
            if ~isempty(refInd)
                EEG = removeRef(EEG, refInd, opt.ref);
                action = 'removed';
            else
                refLoc = resolveChannelLoc(EEG, opt.ref, opt.locfile);
                EEG = addRef(EEG, opt.ref, refLoc);
                action = 'added';
            end

        case 'remove'
            if isempty(refInd)
                error('custom_handleref: Channel ''%s'' not found in dataset.', opt.ref);
            end
            EEG = removeRef(EEG, refInd, opt.ref);
            action = 'removed';

        case 'add'
            if ~isempty(refInd)
                error('custom_handleref: Channel ''%s'' already exists in dataset.', opt.ref);
            end
            refLoc = resolveChannelLoc(EEG, opt.ref, opt.locfile);
            EEG = addRef(EEG, opt.ref, refLoc);
            action = 'added';
    end

    EEG = eeg_checkset(EEG);
    fprintf('custom_handleref: Reference channel ''%s'' was %s.\n', opt.ref, action);

    com = sprintf('EEG = custom_handleref(EEG, %s);', vararg2str(varargin));
end

% =========================================================================
% Helper: Resolve the channel location using a priority-based lookup
%   1. EEG.urchanlocs (guaranteed coordinate match)
%   2. External location file (fallback, may have different nose direction)
%   3. Label only (no coordinates)
% =========================================================================
function loc = resolveChannelLoc(EEG, refLabel, locfile)

    loc = [];

    % Priority 1: Look up from EEG.urchanlocs
    if isfield(EEG, 'urchanlocs') && ~isempty(EEG.urchanlocs)
        idx = find(strcmpi({EEG.urchanlocs.labels}, refLabel));
        if ~isempty(idx)
            loc = EEG.urchanlocs(idx(1));
            fprintf('  Found ''%s'' coordinates in EEG.urchanlocs (matching coordinate system).\n', refLabel);
            return;
        end
    end

    % Priority 2: Look up from external location file
    if ~isempty(locfile)
        if ~exist(locfile, 'file')
            warning('custom_handleref: Location file not found: %s', locfile);
        else
            allLocs = readlocs(locfile);
            idx = find(strcmpi({allLocs.labels}, refLabel));
            if ~isempty(idx)
                loc = allLocs(idx(1));
                fprintf('  Found ''%s'' coordinates in location file (verify nose direction matches dataset).\n', refLabel);
                return;
            else
                warning('custom_handleref: Channel ''%s'' not found in location file.', refLabel);
            end
        end
    end

    % Priority 3: Label only
    if isempty(loc)
        loc = struct('labels', refLabel);
        fprintf('  Warning: No coordinates found for ''%s''. Added with label only.\n', refLabel);
    end
end

% =========================================================================
% Helper: Remove the reference channel
% =========================================================================
function EEG = removeRef(EEG, refInd, refLabel)
    EEG = pop_select(EEG, 'nochannel', {refLabel});
    fprintf('  Removed channel ''%s'' (index %d).\n', refLabel, refInd);
end

% =========================================================================
% Helper: Add a zero-filled reference channel
% =========================================================================
function EEG = addRef(EEG, refLabel, refLoc)

    % Append a row of zeros (handles 2D continuous and 3D epoched data)
    EEG.data(end+1, :, :) = 0;

    % Append the resolved location to chanlocs
    EEG.chanlocs(end+1) = refLoc;

    % Update channel count
    EEG.nbchan = size(EEG.data, 1);

    fprintf('  Added zero-filled channel ''%s'' at index %d.\n', refLabel, EEG.nbchan);
end
