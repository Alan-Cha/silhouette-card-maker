# Dev Container
This Dev Container aims to ensure that development for SCM occurs in the same environment to prevent any encumbrance in terms of errors.

## Instructions

### Install Software
Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and [Visual Studio Code](https://code.visualstudio.com/download).

### Install Container Extension
Within Visual Studio Code, install the ["Dev Containers" extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

### Launch Dev Container
Press `Shift+Ctrl+P` and navigate to `Dev Containers: Open Folder in Container`.
Navigate to the directory of this repository on your PC, and click on the parent folder of the repository (`silhouette-card-maker`).

> [!WARNING]
> If doing plugin development, then the `Refresh Explorer` button may need to be used after fetching images, as images often do not refresh within the file explorer.

> [!WARNING]
> If the Python virtual environment is not active within the Visual Studio Code terminal, then launch a new terminal and it will automatically enter the virtual environment.