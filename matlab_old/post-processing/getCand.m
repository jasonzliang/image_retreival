function [cand,cand_vote,cand_lat,cand_lon] = getCand(cell_idx,query,vdir,qLat)

% TMP QLAT ADDITION FOR BUG FIX

% [cand,cand_vote,cand_lat,cand_lon] = getCand(cell_idx,query,vdir)
% 
% DESCRIPTION
%   This function reads the cell combination vote results and the candidate
%   locations for a given query and cell combination.

% Get cell combination filename string
cell_idx = find(cell_idx)';
for j=1:9
    i = find(j==cell_idx);
    if ~isempty(i)
        idx = find(cell_idx < 10*j,1,'last');
        cell_idx = [ cell_idx(1:i-1,1) ; cell_idx(i+1:idx,1) ; ...
                   cell_idx(i,1) ; cell_idx(idx+1:end,1) ];
    end
end
filestr = 'combined,';
for j=1:length(cell_idx)
    filestr = [filestr,num2str(cell_idx(j)),'-'];
end
filestr = [filestr(1:end-1),'.res'];

% Get cell combination vote results for this group
vote_file = struct2cell(dir(vdir));
vote_file = vote_file(1,:)';
vote_file = vote_file(~cellfun('isempty',strfind(vote_file,['DSC_',num2str(query,'%04d')])));
vote_file = vote_file(~cellfun('isempty',strfind(vote_file,filestr)));
vote_file = vote_file(~cellfun('isempty',strfind(vote_file,num2str(round(qLat*10^5)/10^5,'%.5f'))) ...
                    | ~cellfun('isempty',strfind(vote_file,num2str(floor(qLat*10^5)/10^5,'%.5f'))));
if isempty(vote_file)
    fprintf(['\nDSC_',num2str(query,'%04d'),'\n'])
    fprintf('%.5f\n',floor(qLat*10^5)/10^5)
    fprintf('%.5f\n',round(qLat*10^5)/10^5)
    fprintf([filestr,'\n'])
    error('Combination results not found.')
end
[cand_vote,cand] = textread([vdir,vote_file{1}],'%d%s');

% Get candidate locations and add sift.txt to the end of each candidate
comma_idx = strfind(cand,',');
ncand = length(cand);
cand_lat = zeros(ncand,1);
cand_lon = zeros(ncand,1);
for k=1:ncand
    cand_lat(k) = str2double( ...
        cand{k}( 1:comma_idx{k}-1 ) );
    cand_lon(k) = str2double( ...
        cand{k}( comma_idx{k}+1:end-5 ) );
    cand{k} = [cand{k},'sift.txt'];
end