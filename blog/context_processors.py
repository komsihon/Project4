import random
from ikwen_webnode.blog.models import Post, PostCategory, PostLikes, Photo


def blog_base_data(request):
    rand = random.random()
    suggestions = Post.objects.filter(is_active=True, rand__lte=rand)
    categories = PostCategory.objects.all()
    recent_posts = Post.objects.filter(is_active=True).order_by('created_on')[:5]

    return {
                'categories': categories,
                'recent_posts': recent_posts,
                'suggestions': suggestions[:4],
                'most_consulted': recent_posts[:4],
                'archives': recent_posts,
            }
