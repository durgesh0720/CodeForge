from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from .models import coder
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required



# Create your views here.
def get_first_last_name(full_name):
    parts = full_name.strip().split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
    return first_name, last_name

def landingPage(request):
    if request.user.is_authenticated:
        context = {'coder': request.user}
        return render(request, "welcome.html", context)
    return render(request, "landingPage.html")

def loginPage(request):
     return render(request, "authe.html")

@login_required
def welcomePage(request):
    context = {}
    try:
        coder_instance = coder.objects.get(user=request.user)
        context['coder'] = coder_instance
    except coder.DoesNotExist:
        context['coder'] = None  # Explicitly set to None if the coder instance doesn't exist
    return render(request, 'welcome.html', context)

def signupCoder(request):
    if request.method == "POST":
        username = request.POST.get('username')
        first_name, last_name = get_first_last_name(request.POST.get('fname'))
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Check if passwords match
        if password != confirm_password:
            context = {'error': "Password not matched"}
            return render(request, "authe.html", context)

        try:
            # Create the user if username doesn't already exist
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password  # Don't need to call set_password as create_user already hashes the password
            )
            user.save()
            context = {'msg': "User Created Successfully, Please Login"}
            return render(request, "authe.html", context)

        except Exception as e:
            context = {'error': "Username already exists"}
            return render(request, "authe.html", context)

def loginCoder(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('welcomepage')
        else:
            context = {'error': "Invalid Credentials"}
            return render(request, "authe.html", context)
    return render(request, "authe.html")
        
def logoutCoder(request):
    logout(request)
    return redirect('homepage')
        