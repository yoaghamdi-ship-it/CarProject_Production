from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Inventory
from .serializers import InventorySerializer

@api_view(['GET'])
def car_list_api(request):
    cars = Inventory.objects.all()
    serializer = InventorySerializer(cars, many=True)
    return Response(serializer.data)