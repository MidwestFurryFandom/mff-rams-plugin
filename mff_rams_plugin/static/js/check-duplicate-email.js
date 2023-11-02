checkDuplicateEmails = function(attendee_id) {
    let link = '';
    let modalIdStr = '';
    let hotel_lottery_faq_url = $('#js-script-vars').data('hotel-lottery-faq-url')
    if (event.currentTarget.tagName == "A") {
        event.preventDefault();
        link = event.currentTarget.href;
    } else {
        modalIdStr = event.currentTarget.dataset.bsTarget;
    }
    duplicate_message = '<p>The email address for this registration is used by at least one other registration.</p>' +
                        '<p>Hotel lottery entries are limited to one entry per email address.</p>' +
                        '<p>See <a href="' + hotel_lottery_faq_url + '" target="_blank">our FAQ</a> for more information.</p>'
    $.ajax({
    method: 'POST',
    url: '../hotel_lottery/check_duplicate_emails',
    data: {
        id: attendee_id,
        csrf_token: csrf_token
    },
    success: function(response) {
        if (response.count && parseInt(response.count) > 0) {
            if(link != '') {
                bootbox.confirm({
                    backdrop: true,
                    title: 'Hotel Lottery Notice',
                    message: duplicate_message,
                    buttons: {
                    confirm: { label: 'I understand, take me to the lottery!', className: 'btn-success' },
                    cancel: { label: 'Cancel', className: 'btn-outline-secondary' }
                    },
                    callback: function (result) {
                    if (result) {
                        window.location.href = link;
                    }
                    }
                });
            } else {
                modal = $(modalIdStr);
                modal.find('.duplicate-warning').first().html(duplicate_message);
            }
        } else if (response.count != undefined) {
            if(link != '') {
                window.location.href = link;
            } else {
                modal = $(modalIdStr);
                modal.find('.duplicate-warning').first().html('');
            }
        }
    }
});   
}