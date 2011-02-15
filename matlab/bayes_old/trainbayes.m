function [classifier] = trainbayes(features,classes,weights,classifier_info)

% [classifier] = trainbayes(features,classes,weights,classifier_info)
% 
% First coded 12 Dec 2010 by Aaron Hallquist.
% Latest revision 10 Feb 2011 by Aaron Hallquist.
%
% K = number of training samples
% M = number of features
% C = number of classes
% 
% DESCRIPTION:
%   This function trains a Naive Bayes classifier. It takes as input a list
%   of K training samples with their features and classes and outputs the 
%   priors and feature distributions necessary to classify new samples. If 
%   a feature is absent for a training sample, this is denoted with the 
%   value NaN. Each feature also takes an input assumed distribution.
%   Currently supported distributions are 'Normal' and 'Gamma'.
% 
% INPUT:
%   features:   KxM matrix of features
%   classes:    Kx1 vector of classes
%                   C == max(classes)
%                   classes must contain integers ranging from 1 to C
%   weights:    Kx1 vector of sample weights (influence of sample)
%               This is optional. Default = 1 for all samples
%   classifier_info: Optional input which can be a structure or cell array. 
%                 - If it is left out, all distributions are assumed to be
%                   gamma distributions
%                 - If it is a cell array, the input is assumed to be a 1xM
%                   cell array containing the assumed feature distributions
%                 - If it is a structure, the input is assumed to be a
%                   classifier which we are further training.
% 
% OUTPUT:
%   classifier: Structure with the following elements...
%       .dists:     1xM cell array of strings containing the assumed
%                       distribution for each feature
%       .priors:	Cx1 vector of prior probabilities for the classes
%                       1 == sum(priors)
%       .nsamps:    Cx1 vector containing the number of training samples in
%                       each class:     prios = nsamps / sum(nsamps)
%       .means:     CxM matrix of feature means
%       .vars:      CxM matrix of feature variances
%       .nfeats:    CxM matrix containing the number of features for each
%                       class used to compute means and variances

% Get size parameters
[K,M] = size(features);
C = max(classes);

% Set weights if unspecified
if nargin < 3
    weights = ones(K,1);
end

% Set classifier initial state
if nargin < 4
    classifier.dists = repmat( cellstr('Gamma') , [1,M] );
    classifier.priors = zeros(C,1);
    classifier.nsamps = zeros(C,1);
    classifier.means = zeros(C,M);
    classifier.vars = zeros(C,M);
    classifier.nfeats = zeros(C,M);
elseif iscell(classifier_info)
    classifier.dists = classifier_info;
    classifier.priors = zeros(C,1);
    classifier.nsamps = zeros(C,1);
    classifier.means = zeros(C,M);
    classifier.vars = zeros(C,M);
    classifier.nfeats = zeros(C,M);
else % isstruct(classifier_info)
    classifier = classifier_info;
    if ~isfield(classifier,'dists')
        classifier.dists = repmat( cellstr('Gamma') , [1,M] );
        classifier.priors = zeros(C,1);
        classifier.nsamps = zeros(C,1);
        classifier.means = zeros(C,M);
        classifier.vars = zeros(C,M);
        classifier.nfeats = zeros(C,M);
    elseif ~isfield(classifier,'nsamps')
        classifier.priors = zeros(C,1);
        classifier.nsamps = zeros(C,1);
        classifier.means = zeros(C,M);
        classifier.vars = zeros(C,M);
        classifier.nfeats = zeros(C,M);
    end
    [C,M] = size(classifier.nfeats);
end

% Iterate through classes to compute classifier information
for c=1:C
    class_idx = ( c == classes );
    class_features = features(class_idx,:);
    class_weights = weights(class_idx);
    classifier.nsamps(c) = classifier.nsamps(c) + sum(class_weights);
    % Iterate through each feature to compute its mean and variance
    for m=1:M
        nf_old = classifier.nfeats(c,m);
        mu_old = classifier.means(c,m);
        s2_old = classifier.vars(c,m);
        feat_idx = isfinite(class_features(:,m));
        feat = class_features(feat_idx,m);
        w = weights(feat_idx,1);
        nf_new = nf_old + sum(w);
        mu_new = ( nf_old*mu_old + sum(w.*feat) ) / nf_new;
        mom2 = ( nf_old * ( s2_old + mu_old^2 ) + sum(w.*feat.^2) ) / nf_new;
        s2_new = mom2 - mu_new^2;
        if nf_new == 0
            mu_new = 0;
            s2_new = 0;
        end
        classifier.nfeats(c,m) = nf_new;
        classifier.means(c,m) = mu_new;
        classifier.vars(c,m) = s2_new;
    end
end
% Compute the new class priors
classifier.priors = classifier.nsamps / sum(classifier.nsamps);