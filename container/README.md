The Dockerfile here builds the image that will bundle the Linux releases. This allows linking to a consistent glibc version independant of github runner updates.

The image is Alma Linux 9 based, with glibc 3.34. It has python 3.14.2 built from source, which is optimal for linking.

The image is built by the `build_docker_image.yaml` workflow.

Unlike the rest of the project, this Dockerfile is licensed under the MIT license.
