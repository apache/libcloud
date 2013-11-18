#!/usr/bin/env python
#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#
#
# Script which generates a collage of provider logos from multiple provider
# logo files.
#
# It works in two steps:
#
# 1. Resize all the provider logo files (reduce the dimensions)
# 2. Assemble a final image from the resized images

import os
import sys
import argparse
import subprocess
import random

from os.path import join as pjoin

DIMENSIONS = '150x150'  # Dimensions of the resized image (<width>x<height>)
GEOMETRY = '+4+4'  # How to arrange images (+<rows>+<columns>)

TO_CREATE_DIRS = ['resized/', 'final/']


def setup(output_path):
    """
    Create missing directories.
    """
    for directory in TO_CREATE_DIRS:
        final_path = pjoin(output_path, directory)

        if not os.path.exists(final_path):
            os.makedirs(final_path)


def get_logo_files(input_path):
    logo_files = os.listdir(input_path)
    logo_files = [name for name in logo_files if
                  'resized' not in name and name.endswith('png')]
    logo_files = [pjoin(input_path, name) for name in logo_files]

    return logo_files


def resize_images(logo_files, output_path):
    resized_images = []

    for logo_file in logo_files:
        name, ext = os.path.splitext(os.path.basename(logo_file))
        new_name = '%s%s' % (name, ext)
        out_name = pjoin(output_path, 'resized/', new_name)

        print 'Resizing image: %(name)s' % {'name': logo_file}

        values = {'name': logo_file, 'out_name': out_name,
                  'dimensions': DIMENSIONS}
        cmd = 'convert %(name)s -resize %(dimensions)s %(out_name)s'
        cmd = cmd % values
        subprocess.call(cmd, shell=True)

        resized_images.append(out_name)

    return resized_images


def assemble_final_image(resized_images, output_path):
    final_name = pjoin(output_path, 'final/logos.png')
    random.shuffle(resized_images)
    values = {'images': ' '.join(resized_images), 'geometry': GEOMETRY,
              'out_name': final_name}
    cmd = 'montage %(images)s -geometry %(geometry)s %(out_name)s'
    cmd = cmd % values

    print 'Generating final image: %(name)s' % {'name': final_name}
    subprocess.call(cmd, shell=True)


def main(input_path, output_path):
    if not os.path.exists(input_path):
        print('Path doesn\'t exist: %s' % (input_path))
        sys.exit(2)

    if not os.path.exists(output_path):
        print('Path doesn\'t exist: %s' % (output_path))
        sys.exit(2)

    logo_files = get_logo_files(input_path=input_path)

    setup(output_path=output_path)
    resized_images = resize_images(logo_files=logo_files,
                                   output_path=output_path)
    assemble_final_image(resized_images=resized_images,
                         output_path=output_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assemble provider logos '
                                                 ' in a single image')
    parser.add_argument('--input-path', action='store',
                        help='Path to directory which contains provider '
                             'logo files')
    parser.add_argument('--output-path', action='store',
                        help='Path where the new files will be written')
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)
    output_path = os.path.abspath(args.output_path)

    main(input_path=input_path, output_path=output_path)
