(function() {
  $('a[rel^=sort]').click(function() {
    var sortBy = $(this).attr('rel').replace('sort-', ''),
        reverse = $(this).data('reverse') || false;

    function cmp(a, b) {
      aVal = parseInt($(a).data(sortBy));
      bVal = parseInt($(b).data(sortBy));

      if (aVal < bVal) {
        return (reverse) ? -1 : 1;
      } else {
        return (reverse) ? 1 : -1;
      }
    }

    $('.treasures').append($('.treasures li').sort(cmp));
    $('.nav-pills li').removeClass('active');
    $(this).parent().addClass('active');

    return false;
  });
})();
