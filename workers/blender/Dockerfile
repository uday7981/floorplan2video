# Blender 4.2 LTS + ffmpeg 6 + EGL for headless rendering on RunPod RTX 4090.
# Base: NVIDIA CUDA runtime so OPTIX / CUDA is available for Cycles if we ever need
# it (Workbench + Freestyle don't require CUDA, but EGL still wants a GL driver).
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ARG BLENDER_SERIES=4.2
ARG BLENDER_VERSION=4.2.3
ARG BLENDER_URL=https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    NVIDIA_DRIVER_CAPABILITIES=all \
    BLENDER_DIR=/opt/blender

RUN apt-get update && apt-get install -y --no-install-recommends \
      wget xz-utils ca-certificates gnupg software-properties-common \
      libgl1 libegl1 libgles2 libglvnd0 libgbm1 \
      libxi6 libxkbcommon0 libxkbcommon-x11-0 libxrandr2 libxcursor1 \
      libxinerama1 libxrender1 libxxf86vm1 libsm6 libxext6 \
      libfreetype6 libfontconfig1 libxml2 \
      python3 python3-pip \
 && add-apt-repository -y ppa:savoury1/ffmpeg6 \
 && apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Install Blender 4.2 LTS
RUN mkdir -p ${BLENDER_DIR} \
 && wget -q ${BLENDER_URL} -O /tmp/blender.tar.xz \
 && tar -xJf /tmp/blender.tar.xz -C ${BLENDER_DIR} --strip-components=1 \
 && rm /tmp/blender.tar.xz \
 && ln -s ${BLENDER_DIR}/blender /usr/local/bin/blender \
 && blender --version && ffmpeg -version | head -1

WORKDIR /workspace
COPY scripts /workspace/scripts

# Default: show help if run with no args.
CMD ["blender", "--help"]
