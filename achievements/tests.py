from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from login.tests import get_new_user
from achievements.models import Achievement
from helpers.test_helpers import create_body
from roles.models import BodyRole

class AchievementTestCae(APITestCase):
    """Check if we can create and verify achievement requests."""

    def setUp(self):
        # Fake authenticate
        self.user = get_new_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        # A different user
        self.user_2 = get_new_user()

        # Dummy bodiews
        self.body_1 = create_body()
        self.body_2 = create_body()

        # Body roles
        self.body_1_role = BodyRole.objects.create(
            name="Body1Role", body=self.body_1, permissions='VerA')

    def test_get_achievement(self):
        """Test retrieve method of achievement viewset."""

        achievement_1 = Achievement.objects.create(
            description="Test Achievement", body=self.body_1, user=self.user.profile)

        url = '/api/achievements/%s' % achievement_1.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['description'], achievement_1.description)

    def test_list_achievement(self):
        """Test listing method of achievement viewset."""

        # Create objects, one verified
        Achievement.objects.create(
            description="Test Achievement 1", body=self.body_1, user=self.user.profile)
        Achievement.objects.create(
            description="Test Achievement 2", body=self.body_1, user=self.user.profile, verified=True)
        Achievement.objects.create(
            description="Different User Ach 3", body=self.body_1, user=self.user_2.profile)
        Achievement.objects.create(
            description="Different User Body 4", body=self.body_2, user=self.user_2.profile)

        # Test listing endpoint
        url = '/api/achievements'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        # Test user me list (only verified)
        url = '/api/user-me'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['achievements']), 1)

        # Test body list (without role)
        url = '/api/achievements-body/%s' % self.body_1.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Test body list (with role)
        self.user.profile.roles.add(self.body_1_role)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.user.profile.roles.remove(self.body_1_role)

    def test_achievement_flow(self):
        """Test creation and verification flow of achievements."""

        # Try creating request without body
        data = {
            'title': 'My Big Achievement',
            'image_url': 'http://example.com/image2.png',
            'verified': True,
            'dismissed': True,
        }
        url = '/api/achievements'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 403)

        # Create (malicious) request from user
        data['body'] = str(self.body_1.id)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['verified'], False)
        self.assertEqual(response.data['dismissed'], False)

        # Get achievement id for further use
        achievement_id = response.data['id']

        # Try to verify without privileges
        url = '/api/achievements/%s' % achievement_id
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 403)

        # Acquire privileges
        self.user.profile.roles.add(self.body_1_role)

        # Try to verify after changing body ID (with privilege)
        data['body'] = str(self.body_2.id)
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 400)

        # Try to verify correctly
        data['body'] = str(self.body_1.id)
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200)

        # Invoke delete API
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        # Lose privileges
        self.user.profile.roles.remove(self.body_1_role)

        # Try deleting a new one
        achievement_1 = Achievement.objects.create(
            description="Test Achievement", body=self.body_1, user=self.user.profile)
        url = '/api/achievements/%s' % achievement_1.id
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)