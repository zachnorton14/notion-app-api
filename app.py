from flask import Flask, request, session, jsonify
from flask_cors import CORS
from config import ApplicationConfig
from models import User, Folder, Note
from passlib.hash import pbkdf2_sha256
import json

app = Flask(__name__)  
CORS(app, supports_credentials=True)

app.config.from_object(ApplicationConfig)

@app.route('/')
def index(): 
    return 'home page'

@app.route('/@me')
def find_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({'error':'Unauthorized'}), 401

    user = json.loads(User.objects(pk=user_id).to_json())
    return {
        "user_id": user_id,
        "user": user
    }

@app.route('/users', methods=['POST'])
def new_user():
    if request.method == 'POST':
        newusername = request.json['username']
        newpassword = request.json['password']
        newemail = request.json['email']

        hashPass = pbkdf2_sha256.hash(str(newpassword))
        existing_username = User.objects(username=newusername).first()
        existing_email = User.objects(email=newemail).first()

        if existing_email is not None:
            return jsonify({'error':f'email "{newemail}" is already in use'}), 409
        
        if existing_username is not None:
            return jsonify({'error':f'username "{newusername}" is already in use'}), 409

        User(username=str(newusername), password_hash=str(hashPass), email=str(newemail)).save()
        return jsonify({"message":"Successfully added new user"}), 200

@app.route('/users/<user_id>', methods=['DELETE', 'PUT', 'GET', 'POST'])
def user(user_id):
    if request.method == 'DELETE':
        session_user_id = session.get("user_id")

        if user_id != session_user_id:
            return jsonify({"message": "Could not delete user"}), 401

        user = json.loads(User.objects(pk=user_id).first().to_json())
        username = user['username']

        deleted_user = User.objects(pk=user_id).delete()

        if deleted_user is False:
            return jsonify({"message":"Could not delete user with given id"}), 401

        session["user_id"] = None

        users_folders = []

        for users_folder in json.loads(Folder.objects(creator=username).all().to_json()):
            if users_folder is None:
                print('No folders')
            else: 
                users_folders.append(users_folder['_id']['$oid'])
        
        if users_folders is not None:
            deleted_folder = Folder.objects(creator=username).delete()

            if deleted_folder is False:
                return jsonify({"message":"Could not delete folder with given id"}), 401
            
            for folder_id in users_folders:
                deleted_notes = Note.objects(folder_id=folder_id).delete()

                if deleted_notes is False:
                    return jsonify({"message":"Successfully deleted user's account and folders"}), 200
                
                return { "message": "Successfully deleted user's account and its subcontent" }, 200

        else: return { "message": "Successfully deleted user" }, 200

    if request.method == 'PUT':
        edited_username = request.json['username']
        edited_bio = request.json['bio']
        edited_profile_picture = request.json['profile_picture']

        if not edited_username or not edited_bio or not edited_profile_picture :
            return jsonify({"message":"Edit fields cannot be blank"}), 401

        user = json.loads(User.objects(pk=user_id).first().to_json())
        username = user['username']

        updated_folders = Folder.objects(creator=username).modify(set__creator=edited_username)
        if updated_folders is False:
            return jsonify({"message": "Couldn't update with given username"}), 401

        updated_user = User.objects(pk=user_id).modify(
            set__username=edited_username,
            set__bio=edited_bio,
            set__profile_picture=edited_profile_picture
        )

        if updated_user is True:
            return jsonify({"message":"Could not edit user with specified values"}), 401

        return {"message": "Successful edit"}, 200

    if request.method == 'GET':
        user = json.loads(User.objects(username=user_id).first().to_json())

        if user is None:
            return {"message":"Could not get user"}, 401
        
        return {
            "message":"Successfully got user",
            "user": user
        }, 200

    if request.method == 'POST':
        session["user_id"] = None

        return jsonify({"message": "Successfully logged user out"}), 200


@app.route('/authentication', methods=['POST'])
def login_authentication():
    email = request.json['email']
    password = request.json['password']

    existing_user = User.objects(email=email).first()
    if existing_user is None:
        return jsonify({'error':'Invalid username or password'}), 401
        
    hashed_password = existing_user['password_hash']
        
    if not pbkdf2_sha256.verify(str(password), hashed_password):
        return jsonify({'error':'Invalid username or password'}), 401
        
    user = json.loads(existing_user.to_json())
    session["user_id"] = user['_id']['$oid']

    return {
    "message":"Login was successful",
    "user": user
    }, 200, {'ContentType':'application/json'}

@app.route('/folder', methods=['GET', 'POST'])
def current_user_folders():
    if request.method == 'POST':
        username = request.json['username']
        new_folder = Folder(creator=username).save()

        if new_folder is None:
            return jsonify({"error":"Could not create new folder with given credentials"})

        folder = json.loads(new_folder.to_json())

        return {
            "message": "Successfully created new folder",
            "folder": folder
        }, 200
    
    if request.method == 'GET':
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({'error':'Unauthorized'}), 401

        user = json.loads(User.objects(pk=user_id).first().to_json())
        username = user['username']

        if user is None:
            return jsonify({"message":"Could not get user"}), 401

        folders = []

        for folder in json.loads(Folder.objects(creator=username).all().to_json()):
            folders.append(folder)

        if folders is None:
            return jsonify({"message":"Current user hasn't created any folders"}), 200

        return {
            "message": "Successfully found current user's folders",
            "folders": folders
        }, 200

@app.route('/folders/public', methods=['GET'])
def public_folders():
    if request.method == 'GET':
        all_published_folders = []

        for folder in json.loads(Folder.objects(is_published=True).all().to_json()):
            all_published_folders.append(folder)
    
        if all_published_folders is None:
            return jsonify({"message":"Could not get published folders"}), 401
        
        return {
            "message":"Successfully got all public folders",
            "folders": all_published_folders
        }

@app.route('/folder/<folder_id>', methods=['PUT', 'DELETE', 'POST'])
def folder(folder_id):
    if request.method == 'DELETE':
        deleted_folder = Folder.objects(pk=folder_id).delete()

        if deleted_folder is False:
            return jsonify({"message":"Could not delete folder with given id"}), 401

        deleted_notes = Note.objects(folder_id=folder_id).delete()

        if deleted_notes is False:
            return jsonify({"message":"Could not delete given folders notes"}), 401

        return { "message": "Successfully found folders" }, 200

    if request.method == 'PUT':
        edited_name = request.json['name']

        if edited_name is None:
            return jsonify({"message":"Edit fields cannot be blank"}), 401

        edited_folder = Folder.objects(pk=folder_id).modify(set__name=edited_name)

        if edited_folder is False:
            return jsonify({"message":"Folder name could not be changed"}), 401

        return {"message":"Successfully updated folder name"}, 200

    if request.method == 'POST':
        published_folder = Folder.objects(pk=folder_id).modify(set__is_published=True)

        if published_folder is False:
            return jsonify({"message":"Could not publish folder"}), 401
        
        return {"message":"successfully published folder"}, 200

@app.route('/folder/<folder_id>/note', methods=['GET', 'POST'])
def all_notes(folder_id):
    if request.method == 'GET':
        folder = json.loads(Folder.objects(pk=folder_id).first().to_json())
        user = json.loads(User.objects(username=folder['creator']).first().to_json())
        user_id = user['_id']['$oid']

        if not user_id:
            return jsonify({'error':'Unauthorized'}), 401

        user = json.loads(User.objects(pk=user_id).first().to_json())
        username = user['username']

        notes = []

        for note in json.loads(Note.objects(creator=username, folder_id=folder_id).all().to_json()):
            notes.append(note)

        if notes is None:
            return jsonify({"message":"Current folder has no notes"}), 200

        return {
            "message": "Successfully found notes",
            "notes": notes
        }, 200

    if request.method == 'POST':
        username = request.json['username']
        new_note = Note(creator=username, folder_id=folder_id).save()

        if new_note is None:
            return jsonify({"error":"Could not create new note with given credentials"}), 401

        id = str(new_note.id)

        return {
            "message": "Successfully created new note",
            "id": id
        }, 200

@app.route('/note/<note_id>', methods=['PUT', 'DELETE'])
def note(note_id):
    if request.method == 'PUT':
        edited_name = request.json['name']
        edited_description = request.json['description']

        if not edited_name or not edited_description:
            return jsonify({"message":"Edit fields cannot be blank"}), 401

        updated_note = Note.objects(pk=note_id).modify(
            set__name=edited_name,
            set__description=edited_description
        )

        if updated_note is True:
            return jsonify({"message":"Could not edit user with specified values"}), 401

        return {"message": "Successful edit"}, 200
    
    if request.method == 'DELETE':
        deleted_note = Note.objects(pk=note_id).delete()

        if deleted_note is False:
            return jsonify({"message":"Could not delete note with given id"}), 401

        return { "message": "Successfully found folders" }, 200

@app.route('/note/<note_id>/content', methods=['PUT'])
def note_content(note_id):
    if request.method == 'PUT':
        edit = request.json['edit']

        if edit == '':
            return jsonify({"message":"content's edit field cannot be blank"}), 401

        edited_note = Note.objects(pk=note_id).modify(set__content=edit)

        if edited_note is False:
            return jsonify({"message":"Could not edit note content"}), 401
        
        return {"message":"successfully edited note content"}, 200

