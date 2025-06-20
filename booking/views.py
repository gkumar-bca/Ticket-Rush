from multiprocessing import context
from django.shortcuts import HttpResponseRedirect, render
from django.http import HttpResponse
from django.forms import formset_factory,modelformset_factory
from staff.models import *
from datetime import datetime, date,time,timezone
from django.views.generic.list import ListView
from accounts.views import is_user, user_login_required
from django.contrib.auth.decorators import (user_passes_test)
from .models import *

from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string


def home(request):
    movies = film.objects.filter().values_list('id','movie_name','url', named=True)
    banners = banner.objects.filter().select_related().values_list('movie__id','movie__movie_name','url', named=True)
    return render(request,"index.html", context={'films': movies,'banners':banners})

def movie_detail(request,id):
    context = {}
    context['film'] = film.objects.get(id = id) 
    context ['showtimes'] = show.objects.filter(movie=id,end_date__gte=date.today()).all().values_list('id','showtime',named=True)
    return render(request,"movie_detail.html",context)

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def show_select(request):
    if(request.method == "GET" and len(request.GET)!=0):
        
        date = request.GET['date']
        films = ""
        # add showitme >= current time + 5 min
        shows = show.objects.filter(end_date__gte=date, start_date__lte=date).select_related('movie_id','movie__url','movie__movie_name').order_by('movie_id','showtime').values_list('id','price','showtime','movie','movie__url','movie__movie_name',named=True)
        res_dict = {}
        
        # Grouping shows rows by movie and appending showitmes in a list
        for s in shows:
            # legend of fields: showid 0, price 1, showtime 2, movieid 3, movieurl 4, moviename 5,
            if(s[5] not in res_dict.keys()): 
                #movie doesn't exit in dict
                res_dict[s[5]]={'url':s[4],'price':s[1], 'showtimes':{s[0]:s[2]}, 'movieid':s[3]}
            else: 
                #movie already exists
                res_dict[s[5]]['showtimes'][s[0]]=s[2]            
        
    return render(request,"show_selection.html",context = {'films':res_dict,'date':date,'shows':shows})


def bookedseats(request):
    """
    AJAX seat booking info retrival view funciton
    """
    if request.method == 'GET':
           show_id = request.GET['show_id']
           show_date = request.GET['show_date']
           seats = booking.objects.filter(show=show_id,show_date=show_date).values('seat_num')
           booked = ""
           for s in seats:
            booked+=s['seat_num']+","
           return HttpResponse(booked[:-1])
    else:
           return HttpResponse("Request method is not a GET")


def sendEmail(request,message):
    """
    Function to send Email
    """
    template ="Hello "+request.user.username+'\n'+message

    user_email = request.user.email

    email = EmailMessage(
        'Tickets Confirmation Email',
        template,
        settings.EMAIL_HOST_USER,
        [user_email],
    )

    email.fail_silently = False
    email.send()
    return True

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import user_passes_test
from accounts.views import user_login_required

@csrf_protect
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def payment(request):
    if request.method == "POST":
        # Extract payment details (dummy processing)
        payment_method = request.POST.get('payment_method')
        upi_id = request.POST.get('upi_id', '')
        card_number = request.POST.get('card_number', '')
        card_expiry = request.POST.get('card_expiry', '')
        card_cvv = request.POST.get('card_cvv', '')

        # Dummy validation (you can expand this as needed)
        if payment_method == 'upi' and upi_id:
            # Simulate UPI payment success
            pass
        elif payment_method == 'card' and card_number and card_expiry and card_cvv:
            # Simulate card payment success
            pass
        else:
            # Handle invalid input
            return render(request, 'payment.html', {'error': 'Please provide valid payment details'})

        # Retrieve booking details from session (set in checkout view)
        booking_data = request.session.get('booking_data', {})
        if not booking_data:
            return redirect('show_select')  # Redirect if no booking data

        # Proceed to create booking (same logic as in checkout view)
        show_date = booking_data.get('show_date')
        seats = booking_data.get('seats')
        show_id = booking_data.get('show_id')

        showinfo = show.objects.get(id=show_id)
        num_seats = len(seats.split(","))
        total = showinfo.price * num_seats

        # Create booking
        booking_obj = booking.objects.create(
            booking_code="Random",
            user=request.user,
            show=showinfo,
            show_date=show_date,
            booked_date=datetime.now(timezone.utc),
            seat_num=seats,
            num_seats=num_seats,
            total=total
        )

        # Prepare context for checkout page
        context = {
            "film": film.objects.get(movie_name=showinfo.movie),
            "sdate": show_date,
            "seats": seats,
            "show": showinfo
        }

        # Send confirmation email
        message = "\nYour tickets are successfully booked. Here are the details. \nThe movie is {}. \nThe show is on {}. \nThe show starts at {}. \nYour seat numbers are {}. \n\nThank you,\nBookMyTicket".format(
            context["film"], show_date, showinfo.showtime, seats
        )
        sendEmail(request, message)

        # Clear session data
        del request.session['booking_data']

        return render(request, "checkout.html", context)

    # For GET request, render payment page
    context = {
        'show_date': request.session.get('booking_data', {}).get('show_date', ''),
        'seats': request.session.get('booking_data', {}).get('seats', ''),
        'total': request.session.get('booking_data', {}).get('total', 0)
    }
    return render(request, "payment.html", context)

@csrf_protect
@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def checkout(request):
    if request.method == "POST":
        show_date = request.POST['showdate']
        seats = request.POST['seats']
        show_id = request.POST['showid']

        # Get show info and calculate total
        showinfo = show.objects.get(id=show_id)
        num_seats = len(seats.split(","))
        total = showinfo.price * num_seats

        # Store booking details in session
        request.session['booking_data'] = {
            'show_date': show_date,
            'seats': seats,
            'show_id': show_id,
            'total': total
        }

        # Redirect to payment page
        return redirect('payment')

    return redirect('show_select')  # Redirect if not POST

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def userbookings(request):
    msg=""
    if(request.method == "GET" and len(request.GET)!=0):
        msg = request.GET['ack']

    booking_table = booking.objects.filter(user=request.user).select_related().order_by('-booked_date').values_list('id','show_date','booked_date','show__movie__movie_name','show__movie__url','show__showtime','total','seat_num',named=True)
    
    context = {
        'data':booking_table,
        'msg':msg
    }
    return render(request,"bookings.html",context)

@user_passes_test(user_login_required, login_url='/accounts/usersignin')
def cancelbooking(request,id):
    bobj =  booking.objects.get(id=id)
    message="\nYour tickets are succcessfully Cancelled. Here are the details.\nYour show info{}\nYour Show date {}\nYour seats\n\nThank you,\nBookMyTicket".format(bobj.show,bobj.show_date,bobj.seat_num)
    ack = "Your tickets {} for {} are cancelled successfully".format(bobj.seat_num,bobj.show)
    bobj.delete()
    sendEmail(request,message)
    
    return HttpResponseRedirect("/mybookings?ack="+ack)

