from django.contrib.auth.decorators import login_not_required
from django.core.paginator import Paginator
from django.shortcuts import render

from trips.releases import RELEASES

RELEASES_PER_PAGE = 10


@login_not_required
def releases(request):
    """Plain-language changelog for non-technical users, newest release first."""
    paginator = Paginator(RELEASES, RELEASES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "pages/releases.html", {"releases": page_obj})
