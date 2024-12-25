# E-Ink Desk Display

![Demo Image](demo.jpg)

This physical application writes to an e-ink screen that lives on my desk, providing a summary of the days ahead.

## Setup Instructions

### 1. System Requirements
- Use 32-bit Raspberry Pi OS (formerly Raspbian) Jessie
- Enable I2C and SPI kernel extensions

### 2. Install System Packages
```bash
sudo apt-get update
sudo apt-get install -y \
    python-rpi.gpio \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-tk \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    libopenblas-dev \
    libatlas-base-dev \
    libtiff5-dev \
    libopenjp2-7-dev