The Dockerfile here builds the image that will bundle the Linux releases. This allows linking to a consistent glibc version independant of github runner updates.

The image is Alma Linux 9 based, with glibc 3.34. It has python 3.12.9 built from source, which is optimal for linking. Finally, it contains the most recent version of poetry at the time of building.

The image is built by the `build_docker_image.yaml` workflow.
