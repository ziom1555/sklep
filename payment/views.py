import braintree
from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import weasyprint
from io import BytesIO


def payment_process(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        # Pobieranie tokena nonce.
        nonce = request.POST.get('payment_method_nonce', None)
        # Utworzenie i przesłanie transakcji.
        result = braintree.Transaction.sale({
            'amount': '{:.2f}'.format(order.get_total_cost()),
            'payment_method_nonce': nonce,
            'options': {
                'submit_for_settlement': True
            }
        })
        if result.is_success:
            # Oznaczenie zamówienia jako opłacone
            order.paid = True
            # Zapisanie unikatowego identyfikatora transakcji.
            order.braintree_id = result.transaction.id
            order.save()

            #Utworzenie wiadomosci e-mail zawierajacej rachunek.
            subject = 'Mój sklep - rachunek nr {}'. format(order.id)
            message = 'W załączniku przesyłamy rachunek dla ostatniego zakupu.'
            email = EmailMessage(subject,
                    message,
                    'kubikgrzegorz.kubik49@gmail.com',
                    [order.email])
            #Wygenerowanie dokumentu PDF.
            html = render_to_string('orders/order/pdf.html', {'order': order})
            out = BytesIO()
            stylesheets = [weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')]
            weasyprint.HTML(string=html).write_pdf(out, stylesheets=stylesheets)
            #Dołaczenie pliku w formacie PDF.
            email.attach('order_{}.pdf'.format(order.id),
                         out.getvalue(),
                         'application/pdf')
            #Wysyłanie wiadomosci e-mail.
            email.send()
            
            return redirect('payment:done')
        else:
            return redirect('payment:canceled')
    else:
        # Wygenerowanie tokena
        client_token = braintree.ClientToken.generate()
        return render(request,
                      'payment/process.html',
                      {'order': order,
                       'client_token': client_token})


def payment_done(request):
    return render(request, 'payment/done.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')