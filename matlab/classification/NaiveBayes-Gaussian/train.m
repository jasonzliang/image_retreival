function [classifier] = train(features,classes)

% [classifier] = train(features,classes)
% 
% First coded 12 Dec 2010 by Aaron Hallquist.
% Latest revision 12 Dec 2010 by Aaron Hallquist.
%
% K = number of training samples
% M = number of features
% C = number of classes
% 
% DESCRIPTION:
%   This function trains a Naive Bayes classifier with a Gaussian
%   assumption on the distribution of the features. It takes as input a
%   list of K training samples with their features and classes and outputs
%   the priors and feature distributions necessary to classify new samples.
% 
% INPUT:
%   features:   KxM matrix of features
%   classes:    Kx1 vector of classes
%                   C = max(classes)
%                   classes must contain integers ranging from 1 to C
% 
% OUTPUT:
%   classifier: Structure with the following elements...
%       .priors:	Cx1 vector of prior probabilities for the classes
%                       1 = sum(priors)
%       .means:     CxM matrix of feature means
%       .vars:      CxM matrix of feature variances

% Get size parameters
[K,M] = size(features);
C = max(classes);

% Initialize classifier
classifier.priors = zeros(C,1);
classifier.means = zeros(C,M);
classifier.vars = zeros(C,M);

% Iterate through classes to compute classifier information
for c=1:C
    idx = find( c == classes );
    class_features = features(idx,:);
    classifier.priors(c) = length(idx) / K;
    classifier.means(c) = mean( class_features );
    classifier.vars(c) = var( class_features );
end