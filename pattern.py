#!/usr/bin/env python

# Armon Shariati
# Final
# Usage: ./pattern.py [path_to_data]/*

import sys
import os
import pprint
import itertools as it
import numpy as np
from scipy.spatial.distance import minkowski

def kNN(k, p, train):
    def g(test_sample):
        nn = zip(['']*k, (np.Inf*np.ones(k)).tolist())
        for key in train: 
            for train_sample in train[key]:
                dist = minkowski(test_sample, train_sample, p)
                if  dist < nn[-1][1]:
                    nn[-1] = (key, dist)
                    nn.sort(key=lambda x: x[1])
        nn = [x[0] for x in nn]
        return max(nn, key=nn.count)
    return g

def minimum_distance_classifier(train):
    mean_vectors = extract_mean_vectors(train)
    def g(sample):
        dist = {}
        for key in mean_vectors:
            dist[key] = np.sqrt(np.sum((sample - mean_vectors[key])**2)) 
        return min(dist, key=dist.get)
    return g

def identical_cov_classifier(train):
    mean_vectors = extract_mean_vectors(train)
    sigma = extract_cov_mat(train)
    def g(sample):
        dist = {}
        for key in mean_vectors:
            dist[key] = np.dot(np.dot((sample - mean_vectors[key]), sigma), np.transpose((sample - mean_vectors[key])))
        return min(dist, key=dist.get)
    return g

def pxl_space_bayes_classifier(train):
    freq = extract_freq(train)
    def g(sample):
        accum = []
        for omega_1, omega_2 in it.combinations(freq, 2):
            p = freq[omega_1]
            q = freq[omega_2]
            accum.append( omega_1 if (disc(sample, p, q) > 0) else omega_2) 
        return max(set(accum), key=accum.count)
    return g

def disc(sample, p, q):
    p = np.array([ 0.0033 if x==0 else x for x in p.tolist() ])
    p = np.array([ 0.9967 if x==1 else x for x in p.tolist() ])
    q = np.array([ 0.0033 if x==0 else x for x in q.tolist() ])
    q = np.array([ 0.9967 if x==1 else x for x in q.tolist() ])
    w = np.log( ((p*(1-q)) / (q*(1-p))) )
    w0 = np.sum(np.log( ((1-p) / (1-q)) ))
    return np.sum(sample * w) + w0

def extract_mean_vectors(data):
    class_mean = {}
    for key in data:
        class_mean[key] = np.mean(np.array(data[key]), axis = 0)
    return class_mean

def extract_cov_mat(data):
    cov_mat = []
    for key in data:
        cov_mat.append( np.cov(np.transpose(np.array(data[key]))) )
    return np.linalg.inv(np.mean(np.array(cov_mat), axis=0))

def extract_freq(data):
    freq = {}
    for key in data:
        freq[key] = np.sum(np.array(data[key]), 0) / float(len(data[key]))
    return freq

def extract_pxl_features(data):
    features = {}
    for key in data:
        features[key] = []
        for image in data[key]:
            features[key].append(image.ravel().tolist())
    return features

def extract_moment_features(data):
    moments = {}
    for key in data:
        moments[key] = [(calculate_moments(x)) for x in data[key]]
    scale = rms(moments)
    for key in data:
        moments[key] = (moments[key] / scale).tolist()
    return moments

def rms(data):
    alldata = []
    for key in data:
        alldata = alldata + data[key]
    return np.sqrt( np.mean(np.array(alldata)**2, 0) )

def calculate_moments(image):
    params = [(1,1), (2,1), (1,2), (3,1), (2,2), (1,3), (4,1), (3,2), (2,3), (1,4)]
    center = moment_of_area(image)
    moments = map(central_moment, [image]*10, [center]*10, params)
    return moments

def central_moment(image, center, param):
    xc, yc = center
    p, q = param

    X = np.arange(1, 17).repeat(16,0).reshape(16, 16)
    Y = X.T
    moment = np.sum((X - xc)**p * (Y - yc)**q * image)

    return moment

def moment_of_area(image):
    black_area = float(np.sum(image))
    x_c = central_moment(image, (0, 0), (1, 0)) / black_area
    y_c = central_moment(image, (0, 0), (0, 1)) / black_area
    return (x_c, y_c)

def pad(image, height, width):
    im = np.zeros((16, 16))
    h1_offset = 0 if height >= 16 else (16 - height) / 2
    w1_offset = 0 if width >= 16 else (16 - width) / 2
    h2_offset = 0 if height < 16 else height - 16
    w2_offset = 0 if width < 16 else width - 16
    for i in range(height - h2_offset):
        for j in range(width - w2_offset):
            im[i + h1_offset, j + w1_offset] = \
                    image[i + (h2_offset / 2), j + (w2_offset / 2)]
    return im

def unpack(argv):
    samples = {}

    for arg in argv:
        path, file_name = os.path.split(arg)
        dataset, label = (file_name.split('.')[0].split('-'))[:]

        if dataset not in samples:
            samples[dataset] = {}
        
        samples[dataset][label] = []

        with open(arg) as f:
            data = f.read()
            target_line = 0

            for i, line  in enumerate(data.split('\n')):
                if line.startswith('C'):
                    new_image = []
                    width = int(line.split()[2][1:])
                    baseline = int(line.split()[3][1:])
                    height = int(line.split()[1][1:])
                    target_line = (i + 1) + height
                else:
                    new_image.append([1. if j == 'x' else 0. for j in line])

                    if (i + 1) == target_line:
                        image = np.array(new_image)
                        padded_image = pad(image, height, width)
                        samples[dataset][label].append( padded_image )

    return samples


def out(features, method):
    idx = dict((key, i) for i, key in enumerate(features))
    confusion = np.zeros((11, 11))
    for key in features:
        for sample in features[key]:
            decision = idx[method(sample)]
            confusion[idx[key]][decision] += 1
            if decision != idx[key]:
                confusion[idx[key]][10] += 1
                confusion[10][decision] += 1
    confusion[10][10] = np.sum(confusion[-1])

    pprint.pprint(confusion.tolist())
    return 0

if __name__ == '__main__':
    if sys.argv == 1:
        print('Usage: ')
        sys.exit()

    data = unpack(sys.argv[1:])

    features = {}
    for d in data:
        features[d] = {'moment': extract_moment_features(data[d]), 
                'pixel': extract_pxl_features(data[d])}

    method = []
    method.append(kNN(1, 2, features['A']['moment']))
    method.append(kNN(1, 4, features['A']['moment']))
    method.append(kNN(5, 2, features['A']['moment']))
    method.append(kNN(1, 2, features['A']['pixel']))
    method.append(kNN(5, 2, features['A']['pixel']))

    pprint.pprint('Output for method 1: ')
    out(features['A']['moment'], method[0])
    out(features['B']['moment'], method[0])

    pprint.pprint('Output for method 2: ')
    out(features['A']['moment'], method[1])
    out(features['B']['moment'], method[1])

    pprint.pprint('Output for method 3: ')
    out(features['A']['moment'], method[2])
    out(features['B']['moment'], method[2])

    pprint.pprint('Output for method 4: ')
    out(features['A']['pixel'], method[3])
    out(features['B']['pixel'], method[3])

    pprint.pprint('Output for method 5: ')
    out(features['A']['pixel'], method[4])
    out(features['B']['pixel'], method[4])
