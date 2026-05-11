# RoboArmCheckers

RoboArmCheckers is an autonomous robotic checkers system built using the OpenManipulator RM-X52-TNM, ROS2, OpenCV, and the Raven checkers engine.

The system integrates:
- Computer vision for board and piece detection  
- Game AI for move selection  
- Robotic manipulation for physical move execution  

## Features

- Real-time board detection  
- HSV-based piece segmentation  
- ROS2 robotic arm control  
- Raven engine integration  
- Automated pick-and-place gameplay  
- Human vs robot and autonomous self-play modes  

## Project Structure

- **checkers-board-frontend** – React-based interface for visualisation and control  
- **checkers-board-backend** – Python server handling game logic and communication between components  
- **robomove** – ROS2 package for robotic arm control and motion planning  
- **usefulscripts** – Collection of helper scripts used during development and testing  

*Note: This repository contains the core functional components of the system and does not include all files required to run the system end-to-end. It includes the main backend, frontend, ROS package, and supporting utilities used during development.*

## Hardware

- OpenManipulator RM-X52-TNM  
- Intel RealSense D435i  
- Standard 8×8 checkers board  
## Author

Dara Rattigan  
M.E. Electronic Engineering Final Year Project  
2025–2026
