from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import CarMake, CarModel
from .restapis import get_request, analyze_review_sentiments, post_review
from .populate import initiate


@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    username = data.get('userName')
    password = data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse(
            {"userName": username, "status": "Authenticated"}
        )
    return JsonResponse(
        {"userName": username, "status": "Failed"}
    )


def logout_request(request):
    logout(request)
    return JsonResponse({"userName": ""})


def get_cars(request):
    if not CarMake.objects.exists():
        initiate()
    car_models = CarModel.objects.select_related('car_make')
    cars = [
        {
            "CarModel": cm.name,
            "CarMake": cm.car_make.name
        }
        for cm in car_models
    ]
    return JsonResponse({"CarModels": cars})


def registration(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid HTTP method"}, status=400)
    try:
        data = json.loads(request.body)
        username = data.get("userName")
        password = data.get("password")
        email = data.get("email")
        if not username or not password or not email:
            return JsonResponse({"error": "Please fill out all fields."})
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists."})
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=data.get("firstName", ""),
            last_name=data.get("lastName", ""),
            email=email
        )
        user.save()
        login(request, user)
        return JsonResponse({"userName": username})
    except Exception as e:
        return JsonResponse({"error": str(e)})


def get_dealerships(request, state="All"):
    try:
        if state == "All":
            endpoint = "/fetchDealers"
        else:
            endpoint = f"/fetchDealers/{state}"
        dealerships = get_request(endpoint)
        print("Dealerships fetched:", dealerships)  # Debug line
        return JsonResponse({"status": 200, "dealers": dealerships or []})
    except Exception as e:
        print("Error in get_dealerships:", e)  # Debug line
        return JsonResponse({"status": 500, "error": str(e)}, status=500)





def get_dealer_reviews(request, dealer_id):
    if dealer_id:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint)
        for review_detail in reviews:
            sentiment_resp = analyze_review_sentiments(
                review_detail['review']
            )
            if (
                sentiment_resp is not None
                and 'sentiment' in sentiment_resp
            ):
                review_detail['sentiment'] = sentiment_resp['sentiment']
            else:
                review_detail['sentiment'] = None
        return JsonResponse({"status": 200, "reviews": reviews})
    return JsonResponse({"status": 400, "message": "Bad Request"})


def get_dealer_details(request, dealer_id):
    if dealer_id:
        endpoint = f"/fetchDealer/{dealer_id}"
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    return JsonResponse({"status": 400, "message": "Bad Request"})


def add_review(request):
    if not request.user.is_anonymous:
        data = json.loads(request.body)
        try:
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception:
            return JsonResponse(
                {"status": 401, "message": "Error in posting review"}
            )
    return JsonResponse(
        {"status": 403, "message": "Unauthorized"}
    )
