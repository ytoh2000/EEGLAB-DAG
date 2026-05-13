function [EEG, com] = custom_icflag(EEG, varargin)
% CUSTOM_ICFLAG - Wrapper for pop_icflag with individual category thresholds
%
% Usage:
%   EEG = custom_icflag(EEG, 'Brain', [0 0.2], 'Muscle', [0.8 1], ...)
%
% Categories (in order):
%   1. Brain, 2. Muscle, 3. Eye, 4. Heart, 5. Line Noise, 6. Channel Noise, 7. Other

if nargin < 1, help custom_icflag; return; end

% Default thresh is NaN (ignore all by default)
thresh = NaN(7, 2);

% Define categories
cats = {'Brain', 'Muscle', 'Eye', 'Heart', 'Line_Noise', 'Channel_Noise', 'Other'};

% Parse varargin
for i = 1:2:length(varargin)
    name = varargin{i};
    val = varargin{i+1};
    
    % Find matching category
    idx = find(strcmpi(name, cats) | strcmpi(strrep(name, ' ', '_'), cats));
    if ~isempty(idx)
        if ischar(val)
            % Handle string input like "[0 0.2]"
            val = str2num(val);
        end
        if length(val) == 2
            thresh(idx, :) = val;
        elseif isscalar(val)
            % If only one value given, assume it's min, max is 1
            thresh(idx, :) = [val 1];
        end
    end
end

% Call original pop_icflag
[EEG, com] = pop_icflag(EEG, thresh);

end
