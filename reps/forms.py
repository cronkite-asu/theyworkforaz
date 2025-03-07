from django import forms
from django.conf import settings
from geocoders.google import geocoder
from reps.models import District, Bookmark
from django.contrib.gis.geos import Point
from haystack.query import SearchQuerySet

class WhereForm(forms.Form):
    """form for where a user lives"""
    where = forms.CharField(required=False, label="Where do you live ?", widget=forms.TextInput(attrs={'x-webkit-speech':True}))
    lat = forms.CharField(required=False, label="Latitude", widget=forms.HiddenInput())
    lon = forms.CharField(required=False, label="Longitude", widget=forms.HiddenInput())
    district_id = forms.IntegerField(required=False, label="District", widget=forms.HiddenInput())
    place_id = forms.IntegerField(required=False, label="Place", widget=forms.HiddenInput())
    
    def clean(self):
        """clean attributes"""
        cleaned_data = self.cleaned_data
        where = cleaned_data.get('where')
        if where:
            if len(where.split()) < 3:
                # doesn't look like a whole address, looks like a place - find it from our places DB
                sq = SearchQuerySet().filter(content=where).filter(django_ct="reps.place")
                if len(sq) == 0:
                    self._errors['where'] = self.error_class(['We couldn\'t find that place.  Try providing some more detail.'])
                if len(sq) == 1:
                    cleaned_data['place_id'] = sq[0].object.id
                else:
                    self._errors['place_id'] = self.error_class(['There are more than one possible place with that name - which one did you mean?'])
            else:
                # likely a whole address, geocode it
                geocode = geocoder(settings.GOOGLE_MAPS_API_KEY, lonlat=True)
                location = geocode(where)
                if location[0]:
                    try:
                        district = District.objects.get(area__contains=Point(location[1]))
                        cleaned_data['district_id'] = district.id
                    except District.DoesNotExist, e:
                        try:
                            location = geocode("%s, Arizona, USA" % (cleaned_data['where']))
                            district = District.objects.get(area__contains=Point(location[1]))
                            cleaned_data['district_id'] = district.id
                        except District.DoesNotExist, e:
                            self._errors['where'] = self.error_class(['We couldn\'t recognise that address - is it in Arizona?'])
                else:
                    self._errors['where'] = self.error_class(['We couldn\'t recognise that address - is it a valid address?'])
                if location[1][0]:
                    cleaned_data['lat'] = location[1][1]
                    cleaned_data['lon'] = location[1][0]
        else:
            if not (cleaned_data.get('lat') and cleaned_data.get('lon')):
                self._errors['where'] = self.error_class(['Please fill in an address'])
            else:
                cleaned_data['lat'] = float(cleaned_data.get('lat'))
                cleaned_data['lon'] = float(cleaned_data.get('lon'))
                try:
                    district = District.objects.get(area__contains=Point(cleaned_data.get('lon'),cleaned_data.get('lat')))
                    cleaned_data['district_id'] = district.id                    
                except District.DoesNotExist, e:
                    self._errors['where'] = self.error_class(['We can\'t find your location. Are you in Arizona?'])
        return cleaned_data
        
class BookmarkForm(forms.ModelForm):
    class Meta:
        model = Bookmark
        fields = ['content_type', 'object_id']
        widgets = {
            'content_type' : forms.HiddenInput(),
            'object_id' : forms.HiddenInput(),
        }