FROM quay.io/pypa/manylinux_2_34_x86_64


RUN yum update -y && yum groupinstall 'Development Tools' -y && yum install wget -y && wget https://www.python.org/ftp/python/3.12.9/Python-3.12.9.tgz && tar -xvf Python-3.12.9.tgz
RUN yum install libxcb libxkbcommon libxkbcommon-x11 xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm xcb-util-cursor libva mesa-libGLU libX11 libXext libXrender mesa-libGL openssl-devel bzip2-devel libffi-devel sqlite-devel portaudio-devel -y && cd Python-3.12.9 && ./configure --enable-optimizations --enable-shared && make && make install
RUN rm -rf /Python-3.12.9 && rm -rf Python-3.12.9.tgz

RUN ldconfig /usr/local/lib && ln -sf /usr/local/bin/python3.12 /usr/bin/python3.12 && ln -sf /usr/local/bin/pip3.12 /usr/bin/pip3.12 &&  ln -sf /usr/local/bin/python3.12 /usr/bin/python3 &&  ln -sf /usr/local/bin/pip3.12 /usr/bin/pip3 &&  ln -sf /usr/local/bin/python3.12 /usr/bin/python && ln -sf /usr/local/bin/pip3.12 /usr/bin/pip

LABEL maintainer="usdb_syncer developers"
LABEL org.opencontainers.image.source="https://github.com/randompersona1/some_actions_testing"
LABEL org.opencontainers.image.description="A container to build linux binaries that work on most linux distributions."
LABEL org.opencontainers.image.licenses="MIT"
