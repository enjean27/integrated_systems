#!/usr/bin/env python
import os
import sys
from app import app, db

def runserver():
    """Run the Flask development server"""
    app.run(host='0.0.0.0', port=5000, debug=True)

def initdb():
    """Initialize the database"""
    with app.app_context():
        db.create_all()
        print("Database initialized successfully")

def createsuperuser():
    """Create an admin user"""
    from models import User
    with app.app_context():
        email = input("Enter admin email: ")
        name = input("Enter admin name: ")
        password = input("Enter admin password: ")
        
        if User.query.filter_by(email=email).first():
            print("User with this email already exists")
            return
        
        admin = User(name=name, email=email, role='admin')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user {email} created successfully")

def shell():
    """Open Flask shell"""
    with app.app_context():
        import code
        from models import User, Event, Registration, Attendance, Certificate, Election, Vote
        
        namespace = {
            'app': app,
            'db': db,
            'User': User,
            'Event': Event,
            'Registration': Registration,
            'Attendance': Attendance,
            'Certificate': Certificate,
            'Election': Election,
            'Vote': Vote,
        }
        
        print("Flask Shell. Available objects: app, db, User, Event, Registration, Attendance, Certificate, Election, Vote")
        code.interact(local=namespace)

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <command>")
        print("Commands:")
        print("  runserver      - Run the development server")
        print("  initdb         - Initialize the database")
        print("  createsuperuser - Create an admin user")
        print("  shell          - Open Flask shell")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'runserver':
        runserver()
    elif command == 'initdb':
        initdb()
    elif command == 'createsuperuser':
        createsuperuser()
    elif command == 'shell':
        shell()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
