Transcendence is an innovative web-based application designed to offer a unique and modern Pong gaming experience. Combining advanced technologies, user-friendly interfaces, and strong security practices, the project challenges developers to create a robust and engaging multiplayer platform.

Core Objectives
	•	Develop a single-page web application (SPA) for playing Pong.
	•	Implement real-time multiplayer functionality for seamless online matches.
	•	Ensure compatibility with the latest version of Google Chrome.
	•	Adhere to strict security and performance standards.

Features

Gameplay
	•	Classic Pong gameplay in a modern web environment.
	•	Real-time multiplayer with a matchmaking system.
	•	Tournament mode with automated scheduling and player ranking.

User Management
	•	Secure user registration and authentication.
	•	Customizable profiles with avatars and friend management.
	•	Match history and player statistics tracking.

Security
	•	Passwords stored using robust hashing algorithms.
	•	Protection against SQL injection and XSS attacks.
	•	Full HTTPS integration and input validation.

Technical Requirements
	•	Built as a single-page application.
	•	Developed using vanilla JavaScript for the frontend.
	•	Dockerized deployment for consistent and scalable builds.

Modules

The project includes optional modules for expanding functionality:
	•	Web Development: Backend and frontend frameworks integration.
	•	Gameplay Enhancements: Support for remote players and multiplayer modes.
	•	AI Integration: Introduce an AI opponent with human-like behavior.
	•	Cybersecurity: Implement Two-Factor Authentication (2FA) and JWT for secure access.
	•	DevOps: Logging via ELK stack and monitoring with Prometheus and Grafana.
	•	Graphics: Enhance visuals using advanced 3D technologies like Three.js.

Getting Started

Prerequisites
	•	Docker: Ensure Docker is installed and configured.
	•	Git: Clone the project repository.

Installation and Setup
	1.	Clone the repository:

git clone https://github.com/your-repo/ft_transcendence.git


	2.	Navigate to the project directory:

cd ft_transcendence


	3.	Build and launch the containers:

docker-compose up --build


	4.	Open your browser and go to http://127.0.0.1 to access the application.

Project Structure
	•	Frontend: Developed with vanilla JavaScript for a dynamic and responsive user experience.
	•	Backend: Uses a modular microservices architecture, built with Django and PostgreSQL.
	•	Deployment: Dockerized for seamless deployment and scalability.
