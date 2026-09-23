from rest_framework.routers import DefaultRouter

from .views import OpportunityViewSet, OpportunityCategoryViewSet

router = DefaultRouter()
router.register("categories", OpportunityCategoryViewSet, basename="opportunity-category")
router.register("", OpportunityViewSet, basename="opportunity")

urlpatterns = router.urls
