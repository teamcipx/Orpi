import os
import datetime
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# প্রোডাকশনে ব্যবহারের জন্য সেশন সিক্রেট কি পরিবর্তন করুন
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_change_me")

app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=30)
# Supabase API কানেকশন সেটিংস
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ইমেইল মাস্ক করার ফিল্টার (যেমন: ab***c@domain.com)
def mask_email(email):
    try:
        parts = email.split('@')
        name, domain = parts[0], parts[1]
        if len(name) > 3:
            return f"{name[:2]}***{name[-1]}@{domain}"
        return f"{name[0]}***@{domain}"
    except Exception:
        return "u***@email.com"

app.jinja_env.filters['mask_email'] = mask_email


# ------------------ এডমিন প্যানেল রাউটসমূহ ------------------

# এডমিন ভেরিফিকেশন হেল্পার
def check_admin_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = supabase.table("users").select("is_admin, is_banned").eq("id", user_id).execute().data
    if user and user[0]['is_admin'] and not user[0]['is_banned']:
        return user_id
    return None

# (অন্যান্য কোডের সাথে নিচের নতুন রাউটসমূহ যুক্ত করুন)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    # ১. মেট্রিক্স বা স্ট্যাটিস্টিকস হিসাব করা
    # মোট ইউজার সংখ্যা
    all_users = supabase.table("users").select("id", count="exact").execute()
    total_users = all_users.count if all_users.count is not None else 0
    
    # আজকের নতুন ইউজার সংখ্যা
    today_users_query = supabase.table("users").select("id", count="exact").gte("created_at", today_start).execute()
    today_users = today_users_query.count if today_users_query.count is not None else 0
    
    # মোট ডিপোজিট (অনুমোদিত/Approved)
    total_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").execute().data
    total_deposits = sum(float(d['amount']) for d in total_dep_query)
    
    # আজকের মোট ডিপোজিট
    today_dep_query = supabase.table("deposits").select("amount").eq("status", "Approved").gte("created_at", today_start).execute().data
    today_deposits = sum(float(d['amount']) for d in today_dep_query)
    
    # ২. ইউজার সার্চ ইঞ্জিন
    search_query = request.args.get('search', '').strip()
    users_list = []
    
    if search_query:
        # ইমেইল অথবা ইউজারনেম দিয়ে সার্চ
        u_data = supabase.table("users").select("id, username, email, balance, is_banned") \
            .or_(f"email.ilike.%{search_query}%,username.ilike.%{search_query}%").execute().data
        users_list = u_data
    else:
        # ডিফল্টভাবে শেষ ১০ জন ইউজার প্রদর্শন করা
        u_data = supabase.table("users").select("id, username, email, balance, is_banned") \
            .order("created_at", desc=True).limit(10).execute().data
        users_list = u_data

    return render_template('admin.html', 
                           total_users=total_users, 
                           today_users=today_users, 
                           total_deposits=total_deposits, 
                           today_deposits=today_deposits, 
                           users_list=users_list,
                           search_query=search_query)

# (অন্যান্য কোড অপরিবর্তিত থাকবে, /tasks, /tasks/submit-normal এবং /history রাউটগুলো প্রতিস্থাপন করুন)

# (অন্যান্য কোড অপরিবর্তিত থাকবে, রিভিউ সম্পর্কিত রাউটগুলো নিচের কোড দ্বারা প্রতিস্থাপন করুন)

# ১. শতভাগ নিরাপদ রিভিউ ভিউ ও ইউজার রিভিউ পোস্ট রাউট
@app.route('/reviews', methods=['GET', 'POST'])
def reviews_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("username, is_admin").eq("id", user_id).execute().data[0]
    is_admin = user.get('is_admin', False)
    
    if request.method == 'POST':
        comment = request.form.get('comment')
        rating = int(request.form.get('rating', 5))
        image_url = request.form.get('image_url')
        
        # ডাটাবেজ ক্র্যাশ এড়াতে নিরাপদ ইনসার্ট অবজেক্ট তৈরি
        insert_data = {
            "user_id": user_id,
            "reviewer_name": user['username'],
            "rating": rating,
            "comment": comment,
            "is_admin_fake": False
        }
        
        # ছবি থাকলে তবেই কি (Key) যুক্ত হবে, ফাঁকা বা None পাঠানো হবে না
        if image_url and image_url.strip() != "":
            insert_data["image_url"] = image_url.strip()
            
        try:
            supabase.table("reviews").insert(insert_data).execute()
            flash("আপনার মূল্যবান মতামতটি সফলভাবে জমা হয়েছে।", "success")
        except Exception as e:
            flash(f"রিভিউ জমা দিতে ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
            
        return redirect(url_for('reviews_page'))
        
    # --- নিরাপদ ডাটা কুয়েরি ও ফিল্টারিং ---
    try:
        if is_admin:
            # এডমিন হলে সব রিভিউ দেখতে পারবে
            reviews_data = supabase.table("reviews").select("*").execute().data or []
        else:
            # সাধারণ ইউজারদের জন্য আলাদা আলাদা কুয়েরি করে পাইথনে মার্জ করা (যা শতভাগ ক্র্যাশ-প্রুফ)
            fake_reviews = supabase.table("reviews").select("*").eq("is_admin_fake", True).execute().data or []
            my_reviews = supabase.table("reviews").select("*").eq("user_id", user_id).eq("is_admin_fake", False).execute().data or []
            
            reviews_data = fake_reviews + my_reviews
            
        # তৈরি হওয়ার তারিখ (created_at) অনুযায়ী সাজানো (Newest first)
        reviews_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception:
        reviews_data = [] # কোনো কারণে কুয়েরি ফেইল করলে পেজ ক্র্যাশ না করে ফাঁকা তালিকা দেখাবে
            
    return render_template('reviews.html', reviews=reviews_data, is_admin=is_admin)

# (অন্যান্য রাউটের সাথে নিচের নতুন রাউটটি যুক্ত করুন)

@app.route('/about')
def about():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    return render_template('about.html', user=user)
    

@app.route('/admin/reviews/create', methods=['POST'])
def admin_create_fake_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    fake_name = request.form.get('fake_name')
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment')
    image_url = request.form.get('image_url')
    custom_date = request.form.get('custom_date')
    
    # নিরাপদ ডেটা অবজেক্ট
    review_data = {
        "reviewer_name": fake_name,
        "rating": rating,
        "comment": comment,
        "is_admin_fake": True
    }
    
    if image_url and image_url.strip() != "":
        review_data["image_url"] = image_url.strip()
        
    if custom_date:
        try:
            # ISO এবং PostgreSQL TIMESTAMPTZ সামঞ্জস্যপূর্ণ টাইমস্ট্যাম্প তৈরি (+00:00 offset সহ)
            parsed_date = datetime.datetime.strptime(custom_date, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            review_data["created_at"] = parsed_date.isoformat()
        except Exception as date_err:
            print("Date Parse Error:", date_err)
            
    try:
        supabase.table("reviews").insert(review_data).execute()
        flash("ফেক রিভিউটি সফলভাবে লাইভ করা হয়েছে।", "success")
    except Exception as e:
        # এখানে ত্রুটির সঠিক বিবরণ (যেমন: টেবিল নেই বা কলাম ভুল) ফ্ল্যাশ মেসেজে দেখা যাবে
        error_msg = str(e)
        flash(f"ডাটাবেজ ত্রুটি: {error_msg}", "danger")
        print("Database Insert Error:", error_msg)
        
    return redirect(url_for('reviews_page'))

# ৩. এডমিন কতৃক রিভিউ ডিলিট করার রাউট
@app.route('/admin/reviews/delete', methods=['POST'])
def admin_delete_review():
    user_id = session.get('user_id')
    if not user_id or not check_admin_auth():
        return "Unauthorized Action", 403
        
    review_id = request.form.get('review_id')
    try:
        supabase.table("reviews").delete().eq("id", review_id).execute()
        flash("রিভিউটি সফলভাবে ডিলিট করা হয়েছে।", "success")
    except Exception:
        flash("রিভিউটি ডিলিট করা যায়নি।", "danger")
        
    return redirect(url_for('reviews_page'))
    
@app.route('/tasks')
def tasks():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইউজার ইতিমধ্যে ক্লেইম করা ওয়ান-টাইম টাস্কগুলোর তালিকা
    completed_one_times = supabase.table("user_one_time_tasks") \
        .select("task_name").eq("user_id", user_id).execute().data
    claimed_one_times = [t['task_name'] for t in completed_one_times]
    
    # সফল রেফারেল সংখ্যা যাচাই
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    # প্রোফাইল সম্পূর্ণ করা হয়েছে কিনা যাচাই করা
    is_profile_complete = bool(user.get('phone_number') and user.get('age') and user.get('district'))
    
    # ইউজারের সাবমিট করা পূর্ববর্তী নরমাল টাস্কের ডাটা
    submissions = supabase.table("task_submissions").select("task_id, status").eq("user_id", user_id).execute().data
    submission_map = {s['task_id']: s['status'] for s in submissions}
    
    # এডমিনের তৈরি সমস্ত নরমাল টাস্কসমূহ
    all_normal_tasks = supabase.table("tasks").select("*").order("created_at", desc=True).execute().data
    
    # ফিল্টারিং লজিক: কেবল সেই কাজগুলোই দেখাবে যা ইউজার সাবমিট করেনি অথবা পূর্বে 'Rejected' হয়েছে
    active_normal_tasks = []
    for task in all_normal_tasks:
        status = submission_map.get(task['id'])
        if status is None or status == 'Rejected':
            active_normal_tasks.append(task)

    return render_template('tasks.html', 
                           claimed_one_times=claimed_one_times,
                           success_ref_count=success_ref_count,
                           is_profile_complete=is_profile_complete,
                           all_normal_tasks=active_normal_tasks, # ফিল্টার করা টাস্ক পাঠানো হচ্ছে
                           submission_map=submission_map)


@app.route('/tasks/submit-normal', methods=['POST'])
def submit_normal():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    proof_url = request.form.get('proof_image_url')
    
    if not proof_url:
        flash("দয়া করে কাজের প্রুফ (স্ক্রিনশট) আপলোড করুন।", "danger")
        return redirect(url_for('tasks'))
        
    try:
        # যদি পূর্বে কোনো Rejected সাবমিশন থাকে, তবে তা ডাটাবেজ থেকে মুছে ফেলা হচ্ছে (যাতে কনফ্লিক্ট না হয়)
        supabase.table("task_submissions").delete() \
            .eq("user_id", user_id).eq("task_id", task_id).eq("status", "Rejected").execute()
        
        # নতুন পেন্ডিং সাবমিশন ইনসার্ট করা হচ্ছে
        supabase.table("task_submissions").insert({
            "user_id": user_id,
            "task_id": task_id,
            "proof_image_url": proof_url,
            "status": "Pending"
        }).execute()
        flash("কাজের প্রুফ সফলভাবে জমা দেওয়া হয়েছে। এডমিন ভেরিফাই করবে।", "success")
    except Exception:
        flash("এই কাজটি ইতিমধ্যে প্রক্রিয়াধীন (Pending) অথবা অনুমোদিত (Approved) আছে।", "danger")
        
    return redirect(url_for('tasks'))


@app.route('/history')
def history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # ডিপোজিট, উইথড্রয়াল এবং টাস্ক সাবমিশন হিস্ট্রি রিট্রিভ করা
    deposits = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    withdrawals = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    # জয়েনিং কুয়েরি দিয়ে টাস্ক প্রুফ ও রিওয়ার্ডের তথ্য নিয়ে আসা
    task_history = supabase.table("task_submissions") \
        .select("proof_image_url, status, created_at, tasks(title, reward)") \
        .eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('history.html', deposits=deposits, withdrawals=withdrawals, task_history=task_history)
    
@app.route('/admin/user-action', methods=['POST'])
def admin_user_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    target_id = request.form.get('user_id')
    action = request.form.get('action')
    
    if action == 'ban':
        supabase.table("users").update({"is_banned": True}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "success")
        
    elif action == 'unban':
        supabase.table("users").update({"is_banned": False}).eq("id", target_id).execute()
        flash("ইউজার অ্যাকাউন্ট পুনরায় সক্রিয় (Unbanned) করা হয়েছে।", "success")
        
    elif action == 'delete':
        supabase.table("users").delete().eq("id", target_id).execute()
        flash("ইউজার ডাটাবেজ থেকে সম্পূর্ণ মুছে ফেলা হয়েছে।", "success")
        
    elif action == 'add_balance':
        amount = float(request.form.get('amount', 0))
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": amount}).execute()
        flash(f"সফলভাবে {amount} টাকা যোগ করা হয়েছে।", "success")
        
    elif action == 'add_referral':
        # একটি ডামি রেফারেল যুক্ত করা যা সরাসরি 'Success' স্ট্যাটাস পাবে (রেফারেল বাড়ানোর জন্য)
        supabase.table("referrals").insert({
            "referrer_id": target_id,
            "status": "Success",
            "scheduled_payout_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }).execute()
        
        # সফল রেফারেল এর জন্য ৩০ টাকা বোনাস দেওয়া
        supabase.rpc("increment_balance", {"user_id": target_id, "amount": 30.00}).execute()
        flash("ম্যানুয়ালি ১টি সফল রেফারেল এবং ৩০ টাকা যোগ করা হয়েছে।", "success")
        
    return redirect(url_for('admin_dashboard'))



# (অন্যান্য কোড অপরিবর্তিত থাকবে, কেবল claim_one_time ফাংশনটি নিচে দেওয়া কোড দ্বারা প্রতিস্থাপন করুন)

@app.route('/tasks/claim-one-time', methods=['POST'])
def claim_one_time():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    task_name = request.json.get('task_name')
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইতিমধ্যে ক্লেইম করা হয়েছে কিনা যাচাই
    exists = supabase.table("user_one_time_tasks").select("id").eq("user_id", user_id).eq("task_name", task_name).execute().data
    if exists:
        return jsonify({"status": "error", "message": "এই টাস্কটি ইতিমধ্যে ক্লেইম করা হয়েছে।"})
        
    reward = 0.00
    
    # ইউজারনেম দিয়ে সফল রেফারের মোট সংখ্যা বের করা
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    if task_name == 'profile_update':
        if user.get('phone_number') and user.get('age') and user.get('district'):
            reward = 5.00
        else:
            return jsonify({"status": "error", "message": "আপনার প্রোফাইলের সব তথ্য এখনও পূর্ণ করা হয়নি।"})
            
    elif task_name == 'join_channel':
        reward = 5.00 # ডিরেক্ট ক্লিক ক্লেইম
        
    elif task_name == 'watch_tutorial':
        reward = 5.00 # ডিরেক্ট ক্লিক ক্লেইম
        
    elif task_name == 'refer_3':
        if success_ref_count >= 3:
            reward = 50.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ৩টি সফল রেফারেল সম্পন্ন হয়নি।"})
            
    elif task_name == 'refer_10':
        if success_ref_count >= 10:
            reward = 150.00
        else:
            return jsonify({"status": "error", "message": "আপনার এখনো ১০টি সফল রেফারেল সম্পন্ন হয়নি।"})
    else:
        return jsonify({"status": "error", "message": "অবৈধ টাস্ক রিকোয়েস্ট। "})
        
    # বোনাস যোগ করা এবং ট্র্যাক করা
    supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
    supabase.table("user_one_time_tasks").insert({"user_id": user_id, "task_name": task_name}).execute()
    
    return jsonify({"status": "success", "message": f"সফলভাবে ক্লেইমড! আপনার ব্যালেন্সে ৳ {reward} যোগ করা হয়েছে। "})
    # ৩. নরমাল টাস্ক সাবমিট এপিআই




# ৪. এডমিন টাস্ক প্যানেল (/admin/add)
@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add_task():
    if not check_admin_auth():
        return "Unauthorized Access", 403
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        link = request.form.get('link')
        reward = float(request.form.get('reward'))
        
        supabase.table("tasks").insert({
            "title": title,
            "description": description,
            "link": link,
            "reward": reward
        }).execute()
        flash("নতুন নরমাল টাস্কটি সফলভাবে ডাটাবেজে যুক্ত হয়েছে।", "success")
        return redirect(url_for('admin_add_task'))
        
    # পেন্ডিং প্রুফ সাবমিশনসমূহ রিট্রিভ করা (ভেরিফিকেশনের জন্য)
    pending_submissions = supabase.table("task_submissions") \
        .select("id, proof_image_url, status, created_at, users(username, email), tasks(title, reward)") \
        .eq("status", "Pending").execute().data
        
    return render_template('admin_add.html', pending_submissions=pending_submissions)


# ৫. এডমিন সাবমিশন এপ্রুভ/রিজেক্ট অ্যাকশন
@app.route('/admin/task-action', methods=['POST'])
def admin_task_action():
    if not check_admin_auth():
        return "Unauthorized Action", 403
        
    submission_id = request.form.get('submission_id')
    action = request.form.get('action') # 'approve' or 'reject'
    
    submission = supabase.table("task_submissions").select("*, tasks(reward)").eq("id", submission_id).execute().data
    if not submission:
        flash("সাবমিশন ডাটা পাওয়া যায়নি।", "danger")
        return redirect(url_for('admin_add_task'))
        
    sub = submission[0]
    user_id = sub['user_id']
    reward = float(sub['tasks']['reward'])
    
    if action == 'approve':
        # স্ট্যাটাস Approved করা এবং ব্যালেন্স যোগ করা
        supabase.table("task_submissions").update({"status": "Approved"}).eq("id", submission_id).execute()
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": reward}).execute()
        flash("টাস্ক সাবমিশন এপ্রুভ এবং ইউজারকে রিওয়ার্ড দেওয়া হয়েছে।", "success")
    elif action == 'reject':
        # স্ট্যাটাস Rejected করা
        supabase.table("task_submissions").update({"status": "Rejected"}).eq("id", submission_id).execute()
        flash("টাস্ক সাবমিশন বাতিল (Rejected) করা হয়েছে।", "success")
        
    return redirect(url_for('admin_add_task'))
    
# (অন্যান্য কোড অপরিবর্তিত থাকবে, নিম্নলিখিত রাউটগুলো আপডেট করুন)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_query = supabase.table("users").select("*").eq("email", email).execute()
        
        if user_query.data:
            user = user_query.data[0]
            
            if user.get('is_banned'):
                flash("আপনার অ্যাকাউন্টটি সাময়িকভাবে স্থগিত (Banned) করা হয়েছে।", "danger")
                return render_template('login.html')
                
            if check_password_hash(user['password_hash'], password):
                # সেশন স্থায়ী বা পারমানেন্ট হিসেবে সেট করা হচ্ছে (৩০ দিন মেয়াদে লক থাকবে)
                session.permanent = True
                
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['uid'] = user['uid']
                
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                supabase.table("users").update({"last_login": now}).eq("id", user['id']).execute()
                
                return redirect(url_for('dashboard'))
            
        flash("ভুল ইমেইল অথবা পাসওয়ার্ড।", "danger")
    return render_template('login.html')
    

# ৩. রেফারেল রাউট (ইউনিক আইডি দিয়ে রেফারেল লিংক তৈরি)
@app.route('/referrals')
def referrals():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    user = supabase.table("users").select("uid").eq("id", user_id).execute().data[0]
    
    # অন-ডিমান্ড রেফারেল সময় ও শর্ত পরীক্ষা
    due_referrals = supabase.table("referrals") \
        .select("id, referred_id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Processing") \
        .lte("scheduled_payout_at", now.isoformat()) \
        .execute().data

    for ref in due_referrals:
        referred_id = ref['referred_id']
        ref_user = supabase.table("users").select("last_login").eq("id", referred_id).execute().data
        
        if ref_user:
            last_login_str = ref_user[0]['last_login']
            last_login = datetime.datetime.fromisoformat(last_login_str.replace('Z', '+00:00'))
            twelve_hours_ago = now - datetime.timedelta(hours=12)
            
            new_status = "Success" if last_login >= twelve_hours_ago else "Failed"
            
            supabase.rpc("process_referral_payout", {
                "p_referral_id": ref['id'],
                "p_referrer_id": user_id,
                "p_new_status": new_status,
                "p_reward_amount": 30.00
            }).execute()
            
    referrals_data = supabase.table("referrals") \
        .select("status, created_at, users:referred_id(username, email)") \
        .eq("referrer_id", user_id).execute().data
        
    success_count = sum(1 for r in referrals_data if r['status'] == 'Success')
    processing_count = sum(1 for r in referrals_data if r['status'] == 'Processing')
    failed_count = sum(1 for r in referrals_data if r['status'] == 'Failed')
    total_earnings = success_count * 30.00
        
    # ইউজারনেমের পরিবর্তে UID ব্যবহার করে রেফারেল লিংক জেনারেট
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('referrals.html', 
                           referrals=referrals_data, 
                           ref_link=ref_link,
                           success_count=success_count,
                           processing_count=processing_count,
                           failed_count=failed_count,
                           total_earnings=total_earnings)


# ৪. প্রোফাইল রাউট (ইউনিক আইডি রেফারেল লিংক জেনারেট)
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        phone = request.form.get('phone_number')
        age = request.form.get('age')
        district = request.form.get('district')
        proof_url = request.form.get('avatar_url')
        
        update_data = {}
        if phone: update_data['phone_number'] = phone
        if age: update_data['age'] = int(age) if age.isdigit() else None
        if district: update_data['district'] = district
        if proof_url: update_data['avatar_url'] = proof_url
        
        if update_data:
            supabase.table("users").update(update_data).eq("id", user_id).execute()
            flash("প্রোফাইল তথ্য সফলভাবে আপডেট করা হয়েছে।", "success")
            return redirect(url_for('profile'))
            
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    
    # ইউজারনেমের পরিবর্তে UID ব্যবহার করে রেফারেল লিংক জেনারেট
    ref_link = request.url_root + "register?ref=" + str(user['uid'])
    
    return render_template('profile.html', user=user, ref_link=ref_link)
    
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    # ১. ইউজারের ব্যালেন্স এবং তথ্য নেওয়া
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    # ২. সফল রেফারেলের সংখ্যা বের করা (status = 'Success')
    success_refs_query = supabase.table("referrals") \
        .select("id") \
        .eq("referrer_id", user_id) \
        .eq("status", "Success") \
        .execute().data
    success_ref_count = len(success_refs_query)
    
    # ৩. শর্তসমূহ পরীক্ষা
    meets_referral_cond = (success_ref_count >= 3)
    meets_balance_cond = (balance >= 400.00)
    can_withdraw = (meets_referral_cond and meets_balance_cond)
    
    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        method = request.form.get('method')
        number = request.form.get('number')
        
        if not can_withdraw:
            flash("উইথড্র করার শর্তসমূহ পূরণ হয়নি।", "danger")
        elif amount < 400.00:
            flash("সর্বনিম্ন উইথড্রয়াল পরিমাণ ৪০০ টাকা।", "danger")
        elif amount > balance:
            flash("আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", "danger")
        else:
            # ব্যালেন্স বিয়োগ করা
            supabase.rpc("increment_balance", {"user_id": user_id, "amount": -amount}).execute()
            
            # উইথড্রয়াল রিকোয়েস্ট তৈরি
            supabase.table("withdrawals").insert({
                "user_id": user_id,
                "amount": amount,
                "payment_method": method,
                "payment_number": number,
                "status": "Pending"
            }).execute()
            
            flash("উইথড্রয়াল অনুরোধ সফলভাবে সাবমিট হয়েছে।", "success")
            return redirect(url_for('withdraw'))
            
    # ইউজারের নিজস্ব উইথড্রয়াল হিস্ট্রি রিট্রিভ করা
    history = supabase.table("withdrawals").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    return render_template('withdrawal.html', 
                           user=user, 
                           balance=balance,
                           success_ref_count=success_ref_count,
                           meets_referral_cond=meets_referral_cond,
                           meets_balance_cond=meets_balance_cond,
                           can_withdraw=can_withdraw,
                           history=history)
    
    

@app.route('/store')
def store():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    premium_pkgs = supabase.table("packages").select("*").eq("is_premium", True).order("cost", desc=False).execute().data
    
    # কাস্টম হিস্ট্রি লোড (স্টোরের নিচে দেখানোর জন্য)
    deposit_history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    
    purchase_history = supabase.table("user_packages") \
        .select("bought_at, packages(name, cost, is_premium)") \
        .eq("user_id", user_id).order("bought_at", desc=True).execute().data
    
    return render_template('store.html', 
                           balance=user['balance'], 
                           premium_packages=premium_pkgs,
                           deposit_history=deposit_history,
                           purchase_history=purchase_history)    
# ৫. রিচার্জ বা অ্যাড মানি রাউট
@app.route('/add-money', methods=['GET', 'POST'])
def add_money():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        amount = request.form.get('amount')
        method = request.form.get('method')
        tx_id = request.form.get('transaction_id')
        
        try:
            supabase.table("deposits").insert({
                "user_id": user_id,
                "amount": float(amount),
                "payment_method": method,
                "transaction_id": tx_id,
                "status": "Pending"
            }).execute()
            flash("অনুরোধ জমা হয়েছে। যাচাইকরণের পর ব্যালেন্স যোগ করা হবে।", "success")
        except Exception:
            flash("এই ট্রানজেকশন আইডিটি পূর্বে ব্যবহৃত হয়েছে।", "danger")
            
    history = supabase.table("deposits").select("*").eq("user_id", user_id).order("created_at", desc=True).execute().data
    return render_template('add_money.html', history=history)


@app.route('/register', methods=['GET', 'POST'])
def register():
    ref_by = request.args.get('ref', '')
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        referrer_code = request.form.get('referrer')

        hashed_password = generate_password_hash(password)
        initial_balance = 0.00
        referrer_id = None

        if referrer_code and referrer_code.isdigit():
            ref_uid = int(referrer_code)
            referrer_res = supabase.table("users").select("id").eq("uid", ref_uid).execute()
            if referrer_res.data:
                referrer_id = referrer_res.data[0]['id']
                initial_balance = 100.00
        
        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "balance": initial_balance
        }
        
        try:
            new_user_res = supabase.table("users").insert(user_data).execute()
            if new_user_res.data:
                new_user_id = new_user_res.data[0]['id']
                
                # ফ্রি প্যাকেজের মেয়াদ ৩৬৫ দিন (১ বছর) সেট করে দেওয়া হচ্ছে
                free_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
                supabase.table("user_packages").insert({
                    "user_id": new_user_id,
                    "package_id": 1,
                    "expires_at": free_expiry.isoformat()
                }).execute()
                
                if referrer_id:
                    existing_refs = supabase.table("referrals").select("id").eq("referrer_id", referrer_id).execute().data
                    ref_count = len(existing_refs)
                    
                    if ref_count == 0:
                        delay_hours = 1
                    elif ref_count == 1:
                        delay_hours = 24
                    elif ref_count == 2:
                        delay_hours = 40
                    else:
                        delay_hours = 42
                        
                    scheduled_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=delay_hours)
                    
                    supabase.table("referrals").insert({
                        "referrer_id": referrer_id,
                        "referred_id": new_user_id,
                        "status": "Processing",
                        "scheduled_payout_at": scheduled_time.isoformat()
                    }).execute()
                        
                flash("নিবন্ধন সফল হয়েছে। লগইন করুন।", "success")
                return redirect(url_for('login'))
        except Exception:
            flash("ইউজারনেম অথবা ইমেইলটি ইতিমধ্যে ব্যবহৃত হয়েছে।", "danger")
            
    return render_template('register.html', ref_by=ref_by)




# ২. ড্যাশবোর্ড রাউট (মেয়াদোত্তীর্ণ প্যাকেজ অটো-ডিলিট এবং তথ্য সংগ্রহ)
@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
        
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # নিরাপত্তা ও স্ট্যাবিলিটি আপডেট: মেয়াদ শেষ হওয়া প্যাকেজগুলো অটোমেটিক ডিলিট করা
    supabase.table("user_packages").delete().eq("user_id", user_id).lt("expires_at", now.isoformat()).execute()
        
    user = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    # ডেইলি চেক-ইন ভ্যালিডেশন
    is_daily_eligible = True
    last_checkin_str = user.get('last_daily_checkin')
    if last_checkin_str:
        last_checkin = datetime.datetime.fromisoformat(last_checkin_str.replace('Z', '+00:00'))
        cooldown = datetime.timedelta(hours=24)
        if now < last_checkin + cooldown:
            is_daily_eligible = False
    
    # মেয়াদ (expires_at) সহ ইউজারের সক্রিয় প্যাকেজগুলোর তালিকা রিট্রিভ করা
    owned_pkgs = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(name, duration_hours, yield_amount, is_premium)") \
        .eq("user_id", user_id).execute().data
        
    has_premium_pkg = any(p['packages']['is_premium'] for p in owned_pkgs if p.get('packages'))
    success_refs_query = supabase.table("referrals").select("id").eq("referrer_id", user_id).eq("status", "Success").execute().data
    success_ref_count = len(success_refs_query)
    
    ref_progress = 50 if (success_ref_count >= 3 or has_premium_pkg) else min(success_ref_count / 3, 1.0) * 50
    bal_progress = min(balance / 300, 1.0) * 50
    progress_percent = int(ref_progress + bal_progress)

    notice = "Opti Work এ আপনাকে স্বাগতম! ফ্রি মাইনিং চালু করে প্রতি ৮ ঘণ্টায় ৭ টাকা ক্লেইম করুন। প্রিমিয়াম প্যাকেজ কিনলে আয় আরও বৃদ্ধি পাবে।"

    return render_template('dashboard.html', 
                           user=user, 
                           owned_packages=owned_pkgs, 
                           notice=notice,
                           progress_percent=progress_percent,
                           is_daily_eligible=is_daily_eligible)


# ৩. প্যাকেজ বাই রাউট (প্রিমিয়াম কিনলে ফ্রি প্যাকেজ চিরতরে মুছে ফেলার লজিক সহ)

@app.route('/buy-package', methods=['POST'])
def buy_package():
    user_id = session.get('user_id')
    package_id = request.form.get('package_id')
    if not user_id:
        return redirect(url_for('login'))
        
    pkg = supabase.table("packages").select("*").eq("id", package_id).execute()
    if not pkg.data:
        flash("প্যাকেজ পাওয়া যায়নি।", "danger")
        return redirect(url_for('store'))
        
    cost = float(pkg.data[0]['cost'])
    pkg_name = pkg.data[0]['name']
    
    user = supabase.table("users").select("balance").eq("id", user_id).execute().data[0]
    balance = float(user['balance'])
    
    if balance >= cost:
        # ১. প্রিমিয়াম প্যাকেজ কেনার সাথে সাথে ফ্রি প্যাকেজটি (ID 1) চিরতরে ডিলেট করা
        supabase.table("user_packages").delete().eq("user_id", user_id).eq("package_id", 1).execute()
        
        # ২. ব্যালেন্স কর্তন
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": -cost}).execute()
        
        # ৩. প্রিমিয়াম প্যাকেজের ৩০ দিনের মেয়াদকাল (Expires in 30 days) নির্ধারণ
        expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        
        # ৪. নতুন প্রিমিয়াম প্যাকেজ ডাটাবেজে ইনসার্ট
        supabase.table("user_packages").insert({
            "user_id": user_id,
            "package_id": package_id,
            "last_claimed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "expires_at": expiry_date.isoformat()
        }).execute()
        
        flash(f"{pkg_name} প্যাকেজটি সফলভাবে সক্রিয় করা হয়েছে। মেয়াদ ৩০ দিন।", "success")
    else:
        shortage = cost - balance
        flash(f"ব্যালেন্স অপর্যাপ্ত! {pkg_name} প্যাকেজটি কিনতে আপনার আরও ৳ {shortage:.2f} লাগবে। দয়া করে এড মানি করুন।", "danger")
        
    return redirect(url_for('store'))


# ৪. কাস্টম ইন্ডিভিজুয়াল প্যাকেজ ক্লেইম এপিআই (সবুজ গ্লোয়িং টাইমার এবং একক ক্লেইম হ্যান্ডলিং)
@app.route('/claim-mining', methods=['POST'])
def claim_mining():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    # ক্লায়েন্ট থেকে পাঠানো নির্দিষ্ট ইউজার-প্যাকেজ আইডি রিট্রিভ করা
    user_package_id = request.json.get('user_package_id')
    if not user_package_id:
        return jsonify({"status": "error", "message": "অবৈধ মাইনিং রিকোয়েস্ট।"}), 400
        
    # নির্দিষ্ট প্যাকেজ চেক করা
    pkg_query = supabase.table("user_packages") \
        .select("id, last_claimed_at, expires_at, packages(yield_amount, duration_hours)") \
        .eq("id", user_package_id).eq("user_id", user_id).execute().data
        
    if not pkg_query:
        return jsonify({"status": "error", "message": "প্যাকেজটি পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।"}), 404
        
    record = pkg_query[0]
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # মেয়াদ চেক
    if record.get('expires_at'):
        expires_at = datetime.datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))
        if now > expires_at:
            # মেয়াদোত্তীর্ণ নোড রিমুভ
            supabase.table("user_packages").delete().eq("id", user_package_id).execute()
            return jsonify({"status": "error", "message": "এই মাইনিং প্যাকেজটির মেয়াদ শেষ হয়ে গেছে।"}), 400
            
    last_claim = datetime.datetime.fromisoformat(record['last_claimed_at'].replace('Z', '+00:00'))
    cooldown = datetime.timedelta(hours=record['packages']['duration_hours'])
    
    if now >= last_claim + cooldown:
        # শেষ ক্লেইমের সময় আপডেট
        supabase.table("user_packages").update({"last_claimed_at": now.isoformat()}).eq("id", user_package_id).execute()
        # ব্যালেন্স অ্যাড করা
        yield_amount = float(record['packages']['yield_amount'])
        supabase.rpc("increment_balance", {"user_id": user_id, "amount": yield_amount}).execute()
        
        return jsonify({"status": "success", "message": f"৳ {yield_amount} সফলভাবে ক্লেইমড!"})
    else:
        return jsonify({"status": "error", "message": "এই নোডের মাইনিং প্রসেস এখনও সম্পন্ন হয়নি।"})


# (অন্যান্য কোড অপরিবর্তিত থাকবে, /referrals এবং /profile রাউট দুটি প্রতিস্থাপন করুন)

# ৮. লগআউট
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
