# 🚀 YACS Local Development Setup Guide

Welcome to YACS (Yet Another Course Scheduler)! This guide will walk you through setting up the full stack on your local machine.

---

## 1. Prerequisites

Before we start, make sure you have these tools installed:

* **Git**: [Download Git](https://git-scm.com/downloads)
* **Docker Desktop**: This is required to run the backend services and database.
    * [Download for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
    * [Download for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
    * *Note: Open the Docker Desktop app after installing to ensure the Docker Engine is running.*
* **Node Version Manager (NVM)**: 

    **(Open a NEW terminal window after installing NVM)**
    * **macOS/Linux**: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash`
    * **Windows**: Download `nvm-setup.exe` from the [nvm-windows repository](https://github.com/coreybutler/nvm-windows/releases/latest).
    


## 2. Forking & Cloning

1. Open the YACS Repo: https://github.com/JoJo-ESC/yacs
2. Click the fork button on the top right corner of the Repository.
3. Clone the forked git repository to your computer

    ```
    git clone https://github.com/[YourProfile]/yacs.git
    ```

## 3. Setup Docker

Change working directory to yacs
```
cd yacs
```
1. Open Docker Desktop, to make sure the docker engine is running
2. Run the container, which uses our `docker-compose.yml`. Make sure the working directory is in `yacs`.
    ```
    docker compose -p new_yacs up -d
    ```

## 4. Setup Live Frontend
1. Setup Node Version
    * **macOS Users**:
        ```
        source ~/.zshrc   # or ~/.bashrc if using bash
        nvm install 20
        nvm use 20
        ```
    * **Windows Users**:
        ```
        nvm install 20
        nvm use 20
        ```
2. Set working directory to frontend and install npm dependencies.
    ```
    cd frontend
    npm install
    ```
3. Start the live frontend UI, locally hosted on `localhost:3000`
    ```
    npm start
    ```

## Localhost Ports
- Development UI: `http://localhost:3000`
- FastAPI: `http://localhost:8000`
- Postgres: `http://localhost:5432`

## Developer Notes
- Remember to stop the YACS docker container when you're done to relieve system resources. Click the red Stop button under Actions in Docker Desktop next to `new_yacs`.