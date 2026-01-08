#!/usr/bin/env bash
# Setup environment for building Android kernels on Arch Linux
# Author: GarryStraitYt
# Compatible with kernel 5.x / 6.x builds using Android NDK r25c

set -euo pipefail
DATE_TIME="$(date)"
# --- CONFIGURATION ---
NDK_VERSION="android-ndk-r25c"
NDK_ZIP="${NDK_VERSION}-linux.zip"
NDK_URL="https://dl.google.com/android/repository/${NDK_ZIP}"
NDK_DIR="$PWD/${NDK_VERSION}"
KBUILD_BUILD_TIMESTAMP="${DATE_TIME}"

echo "==> Android Kernel Build Environment Setup (Arch Linux)"
echo

# --- ASK FOR BUILD USER & HOST ---
read -rp "Enter build user (e.g., your username): " BUILD_USER
read -rp "Enter build host (e.g., hostname or machine name): " BUILD_HOST
echo

echo "==> Checking required dependencies..."

# List of required system packages
REQUIRED_PKGS=(
  base-devel
  cpio
  openssl
  lz4
  python
  wget
  unzip
  llvm
  clang
  lld
  bc
  flex
  bison
)

MISSING_PKGS=()

# Check each package
for pkg in "${REQUIRED_PKGS[@]}"; do
  if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
    MISSING_PKGS+=("$pkg")
  fi
done

# Install missing pacman packages
if (( ${#MISSING_PKGS[@]} > 0 )); then
  echo "==> Installing missing system packages: ${MISSING_PKGS[*]}"
  sudo pacman -S --needed --noconfirm "${MISSING_PKGS[@]}"
else
  echo "==> All system dependencies already installed."
fi

echo "==> Checking ncurses5 compatibility library..."

if ! ldconfig -p | grep -q "libncurses.so.5"; then
  echo "==> ncurses5-compat-libs not found."

  if ! command -v yay >/dev/null 2>&1; then
    echo "==> Installing yay (AUR helper)..."
    git clone https://aur.archlinux.org/yay.git
    pushd yay >/dev/null
    makepkg -si --noconfirm
    popd >/dev/null
    rm -rf yay
  fi

  echo "==> Installing ncurses5-compat-libs from AUR..."
  yay -S --needed --noconfirm ncurses5-compat-libs
else
  echo "==> ncurses5 compatibility library already installed."
fi


# --- DOWNLOAD & EXTRACT ANDROID NDK ---
if [ ! -d "$NDK_DIR" ]; then
  echo "==> Downloading Android NDK ${NDK_VERSION}..."
  wget -q "$NDK_URL"
  echo "==> Extracting NDK..."
  unzip -q "$NDK_ZIP"
  rm "$NDK_ZIP"
else
  echo "==> Android NDK already present: $NDK_DIR"
fi

# --- DETERMINE SHELL RC FILE ---
SHELL_NAME=$(basename "$SHELL")
if [[ "$SHELL_NAME" == "bash" ]]; then
  RC_FILE="$HOME/.bashrc"
elif [[ "$SHELL_NAME" == "zsh" ]]; then
  RC_FILE="$HOME/.zshrc"
else
  RC_FILE="$HOME/.bashrc"
fi

# --- SET ENVIRONMENT VARIABLES ---
echo "==> Setting up environment variables..."
export NDK_HOME="$NDK_DIR"
export PATH="$NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH"
export ARCH=arm64
export SUBARCH=arm64
export CLANG_TRIPLE=aarch64-linux-gnu-
export CROSS_COMPILE=aarch64-linux-gnu-
export KBUILD_BUILD_USER="$BUILD_USER"
export KBUILD_BUILD_HOST="$BUILD_HOST"
export KBUILD_BUILD_TIMESTAMP="$KBUILD_BUILD_TIMESTAMP"

# --- ADD ENV VARIABLES PERMANENTLY ---
echo
read -rp "Would you like to make these environment variables permanent? [y/N]: " ADD_PERM
if [[ "$ADD_PERM" =~ ^[Yy]$ ]]; then
  {
    echo ""
    echo "# Android kernel build environment"
    echo "export NDK_HOME=\"$NDK_DIR\""
    echo "export PATH=\"\$NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:\$PATH\""
    echo "export ARCH=arm64"
    echo "export SUBARCH=arm64"
    echo "export CLANG_TRIPLE=aarch64-linux-gnu-"
    echo "export CROSS_COMPILE=aarch64-linux-gnu-"
    echo "export KBUILD_BUILD_USER=\"$BUILD_USER\""
    echo "export KBUILD_BUILD_HOST=\"$BUILD_HOST\""
    echo "export KBUILD_BUILD_TIMESTAMP=\"$KBUILD_BUILD_TIMESTAMP\""
  } >> "$RC_FILE"

  echo "✅ Added environment variables to $RC_FILE"
else
  echo "ℹ️ Skipped adding variables permanently."
fi

# --- DONE ---
echo
echo "✅ Android kernel build environment setup complete!"
echo
echo "Next steps:"
echo "------------------------------------------------------------"
echo "1. Reload your shell (if you made variables permanent):"
echo "     source $RC_FILE"
echo
echo "2. Verify the NDK toolchain is accessible:"
echo "     clang --version"
echo
echo "3. (Optional) Add KernelSU:"
echo "     ./ksu.sh"
echo
echo "4. Build your kernel:"
echo "     make O=build CC=clang LD=ld.lld -j\$(nproc)"
echo
echo "Environment summary:"
echo "  • NDK_HOME=$NDK_HOME"
echo "  • KBUILD_BUILD_USER=$BUILD_USER"
echo "  • KBUILD_BUILD_HOST=$BUILD_HOST"
echo "  • KBUILD_BUILD_TIMESTAMP=$KBUILD_BUILD_TIMESTAMP"
echo "------------------------------------------------------------"
