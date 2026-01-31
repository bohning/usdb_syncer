FROM quay.io/pypa/manylinux_2_34_x86_64:latest

RUN rm -rf /opt/python

LABEL maintainer="usdb_syncer developers"
LABEL org.opencontainers.image.base.name="quay.io/pypa/manylinux_2_34_x86_64:latest"
LABEL org.opencontainers.image.source="https://github.com/bohning/usdb_syncer"
LABEL org.opencontainers.image.description="A container to build linux binaries that work on most linux distributions."
LABEL org.opencontainers.image.licenses="MIT"

RUN yum update -y && yum groupinstall 'Development Tools' -y && yum install wget -y && wget https://www.python.org/ftp/python/3.14.2/Python-3.14.2.tgz && tar -xvf Python-3.14.2.tgz
RUN yum install libxcb libxkbcommon libxkbcommon-x11 xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-wm xcb-util-cursor libva mesa-libGLU libX11 libXext libXrender mesa-libGL openssl-devel bzip2-devel libffi-devel sqlite-devel -y && cd Python-3.14.2 && ./configure --enable-optimizations --enable-shared && make && make install
RUN rm -rf /Python-3.14.2 && rm -rf Python-3.14.2.tgz

RUN ldconfig /usr/local/lib && ln -sf /usr/local/bin/python3.14 /usr/bin/python3.14 && ln -sf /usr/local/bin/pip3.14 /usr/bin/pip3.14 &&  ln -sf /usr/local/bin/python3.14 /usr/bin/python3 &&  ln -sf /usr/local/bin/pip3.14 /usr/bin/pip3 &&  ln -sf /usr/local/bin/python3.14 /usr/bin/python && ln -sf /usr/local/bin/pip3.14 /usr/bin/pip
