from flask import render_template, request, session, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from . import chat_bp
from ..utils import generate_unique_code, rooms 
from ..models import db, Code, GlobalLeaderboard, User, Friendship
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

#~~~ Dashboard (logged in) route block ~~~#
@chat_bp.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "POST":
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        room_id = code #renamed bc it was confusing in this function's context

        if join != False and not code: 
            return render_template("dashboard.html", error="Please enter a room code.", name=current_user.username)
        
        

        if create != False: 
            room_id = generate_unique_code(4)

            rooms[room_id] = {
                "members": 0,
                "messages": [],
                "current_code": None,
                "used_snippets": set(),
                "game_active": False,
                "snippets_completed": 0,
                "ready_users": set(),  
                "max_snippets": 5      
            }
            current_app.logger.info(f"User {current_user.username} created room {room_id}") #log
       
        elif code not in rooms: 
            return render_template("dashboard.html", error="Room does not exist", code=code, name=current_user.username)
        
        session["room"] = room_id
        session["name"] = current_user.username
        return redirect(url_for("chat.room"))

    leaderboard = db.session.query(GlobalLeaderboard).order_by(GlobalLeaderboard.score.desc()).all()

    pending_requests = Friendship.query.options(joinedload(Friendship.sender)).filter(
        Friendship.friend_id == current_user.id,
        Friendship.status == 'pending'
    ).all()

    return render_template('dashboard.html', name=current_user.username, leaderboard=leaderboard, pending_requests=pending_requests)



#~~~ Room route block ~~~#
@chat_bp.route("/room")
@login_required
def room():
    room_id = session.get("room") 
    name = session.get("name")   

    if room_id is None or name is None or room_id not in rooms:
        current_app.logger.warning(f"Access to /room denied or invalid. Room: {room_id}, Name: {name}, Room exists: {room_id in rooms if room_id else 'N/A'}")
        return redirect(url_for("main.intro")) 
    
    if rooms[room_id]["current_code"] is None:
        random_code_obj = Code.query.order_by(db.func.rand()).first()
        rooms[room_id]["current_code"] = random_code_obj 

    #~~~ Logs ~~~#
        if random_code_obj: 
            current_app.logger.info(f"Loaded initial code snippet {random_code_obj.id} for room {room_id}")
        else:   
            current_app.logger.warning(f"No code snippets available for room {room_id}. 'current_code' is None.")


    return render_template(
        "room.html", 
        code=room_id, 
        messages=rooms[room_id]["messages"],
        snippet=rooms[room_id]["current_code"].full_code
    )

#~~~ Friend system block ~~~#
@chat_bp.route("/add_friend/<username>", methods=['POST'])
@login_required
def add_friend(username):
    if current_user.username == username:
        return jsonify(error="You cannot add yourself"), 400

    friend = User.query.filter_by(username=username).first_or_404()
    
    existing = Friendship.query.filter(or_(
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id),
            (Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id)
        )).first()

    if existing:
        if existing.status == 'pending':
            return jsonify(error="Friend request already pending"), 400
        if existing.status == 'accepted':
            return jsonify(error="Already friends"), 400
            
    new_request = Friendship(
        user_id=current_user.id,
        friend_id=friend.id,
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify(success=True, message=f"Request sent to {username}")

@chat_bp.route("/respond_request/<int:request_id>/<action>", methods=['POST'])
@login_required
def respond_request(request_id, action):
    req = Friendship.query.get_or_404(request_id)

    if req.friend_id != current_user.id:
        return jsonify(error="Unauthorized"), 403

    try:
        if action == 'accept':
            req.status = 'accepted'
            db.session.commit()
            return jsonify(success=True, message="Friend request accepted")
        else:
            db.session.delete(req)
            db.session.commit()
            return jsonify(success=True, message="Request declined")
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

@chat_bp.route("/search_users")
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    
    users = User.query.filter(
        User.username.ilike(f'%{query}%'),
        User.id != current_user.id
    ).limit(10).all()
    
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'score': u.score if u.score else 0
    } for u in users])