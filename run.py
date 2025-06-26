from app import create_app

app = create_app()

if __name__ == '__main__':
    # This runs the app using Flask's built-in development server.
    # It's great for testing but not for production.
    # For production, we will use Gunicorn.
    app.run(host='0.0.0.0', port=8080, debug=True)