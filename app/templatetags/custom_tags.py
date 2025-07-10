from django import template
from django.utils.safestring import mark_safe
register = template.Library()
import json


@register.filter
def unread_messages(messages):
    if hasattr(messages, 'filter'):
        return messages.filter(status='UNREAD').count()
    return 0


@register.filter
def get_related_dori_data(related_dori_data, kasallik_id):
    kasallik_id_str = str(kasallik_id)
    dori_list = related_dori_data.get(kasallik_id_str, [])
    return json.dumps(dori_list)


@register.simple_tag(name='pagination')
def pagination(page: int = 1, page_size: int = 10, total: int = 0, search: str = ''):
    search_param = f'&search={search}' if search else ''
    page = int(page)
    page_size = int(page_size)
    total = int(total)
    if total < 10:
        return ''
    total_pages = total // page_size
    extra_pages = total % page_size

    if extra_pages > 0:
        total_pages += 1

    if page > total_pages:
        page = total_pages
    elif page < 1:
        page = 1

    start = page // 5
    end = page % 5

    # interval example page 2 is between 0 and 5 pages
    start = start * 5
    end = (1 if end != 0 else 0) * 5 + start

    if start == end:
        start -= 5

    if start == 0:
        start += 1

    if end > total_pages:
        end = total_pages

    if start < 0:
        start = 0
        end = 0

    content = """
        <div class="d-flex justify-content-between align-items-center flex-wrap">
            <div class="d-flex flex-wrap py-2 mr-3">
                <ul class="pagination">
        """

    is_first_enabled = page - 1 >= 1
    is_last_enabled = total_pages - page >= 1

    content += f"""
    <li class="page-item {'disabled' if not is_first_enabled else ''}">
        <a class="page-link" href="?page=1&page_size={page_size}{search_param}" 
            class="btn btn-icon btn-sm btn-light mr-2 my-1">
            <i class="fa fa-angle-double-left"></i>
        </a>
    </li>
        """

    content += f"""
    <li class="page-item {'disabled' if not is_first_enabled else ''}">
        <a class="page-link" href="?page={page - 1}&page_size={page_size}{search_param}" 
            class="btn btn-icon btn-sm btn-light mr-2 my-1">
            <i class="fa fa-angle-left"></i>
        </a>
    </li>
        """

    if start > 1:
        content += f"""
        <li class="page-item">
            <a class="page-link" href="?page={start - 1}&page_size={page_size}{search_param}" class="btn btn-icon btn-sm border-0 btn-light mr-2 my-1">
                ...
            </a>
         </li>
            """

    for i in range(start, end + 1):
        if i == 0:
            i = 1
        content += f"""
        <li class="page-item {'active' if page == i else ''}">
            <a class="page-link" href="?page={i}&page_size={page_size}{search_param}" 
                class="btn btn-icon btn-sm border-0 btn-light mr-2 my-1">
                {i}
            </a>
        </li>
            """

    if end != total_pages:
        content += f"""
        <li class="page-item">
            <a class="page-link" href="?page={end + 1}&page_size={page_size}{search_param}" class="btn btn-icon btn-sm border-0 btn-light mr-2 my-1">
                ...
            </a>
        </li>
            """

    content += f"""
    <li class="page-item {'disabled' if not is_last_enabled else ''}">
        <a class="page-link" href="?page={page + 1}&page_size={page_size}{search_param}" 
            class="btn btn-icon btn-sm btn-light mr-2 my-1">
            <i class="fa fa-angle-right"></i>
        </a>
    </li>
        """

    content += f"""
    <li class="page-item {'disabled' if not is_last_enabled else ''}">
        <a class="page-link" href="?page={total_pages}&page_size={page_size}{search_param}" 
            class="btn btn-icon btn-sm btn-light mr-2 my-1">
            <i class="fa fa-angle-double-right"></i>
        </a>
    </li>
        """

    content += f"""
                </ul>
            </div>
            <div class="d-flex align-items-center py-3">  
                <div class="dropdown">
                  <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton1" data-bs-toggle="dropdown" aria-expanded="false">
                    {page_size}
                  </button>
                  <ul class="dropdown-menu" aria-labelledby="dropdownMenuButton1">
                    <li><a class="dropdown-item" href="?page=1&page_size=10{search_param}">10</a></li>
                    <li><a class="dropdown-item" href="?page=1&page_size=15{search_param}">15</a></li>
                    <li><a class="dropdown-item" href="?page=1&page_size=20{search_param}">20</a></li>
                    <li><a class="dropdown-item" href="?page=1&page_size=30{search_param}">30</a></li>
                  </ul>
                </div>
                <span class="text-muted"> {page * page_size if page * page_size < total else total} of {total}</span>
            </div>
        </div>
        """

    return mark_safe(content)
