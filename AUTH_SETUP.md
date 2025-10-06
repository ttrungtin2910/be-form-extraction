# Authentication Setup Documentation

## 🔐 Overview

This application now includes a complete JWT-based authentication system with the following features:

- User login/logout
- JWT token-based authentication
- Role-based access control (Admin, User, Viewer)
- Protected API endpoints
- Frontend authentication state management

## 👥 Default User Accounts

### Admin Account
- **Username:** `tin.trantrung`
- **Password:** `secret`
- **Full Name:** Trần Trung Tín
- **Role:** Admin
- **Permissions:** Full access to all features

### User Accounts
- **Username:** `thao.nguyentrang`
- **Password:** `secret`
- **Full Name:** Nguyễn Trang Thảo
- **Role:** User

- **Username:** `vin.nguyenthai`
- **Password:** `secret`
- **Full Name:** Nguyễn Thái Vĩn
- **Role:** User

### Test/Viewer Accounts
- **Username:** `testuser1`
- **Password:** `secret`
- **Full Name:** Test User 1
- **Role:** Viewer

- **Username:** `testuser2`
- **Password:** `secret`
- **Full Name:** Test User 2
- **Role:** Viewer

## 🚀 Backend Setup

### 1. Environment Variables

Add to your `.env` file:
```bash
# JWT Secret Key (used for token signing)
API_SECRET_KEY=your-secret-api-key-here-min-32-chars
```

### 2. API Endpoints

#### Login
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "tin.trantrung",
  "password": "secret"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "tin.trantrung",
  "full_name": "Trần Trung Tín",
  "role": "admin"
}
```

#### Get Current User
```bash
GET /auth/me
Authorization: Bearer <token>

Response:
{
  "username": "tin.trantrung",
  "full_name": "Trần Trung Tín",
  "email": "tin.trantrung@example.com",
  "disabled": false,
  "role": "admin"
}
```

#### Logout
```bash
POST /auth/logout
Authorization: Bearer <token>

Response:
{
  "success": true,
  "message": "Logged out successfully"
}
```

### 3. Protected Endpoints

All existing endpoints now support both:
1. **API Key Authentication** (for service-to-service)
2. **JWT Token Authentication** (for user sessions)

Priority: JWT Token > API Key

Example:
```bash
GET /images/
Authorization: Bearer <jwt-token>
```

## 🎨 Frontend Setup

### 1. Environment Variables

Add to your `.env` file:
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_API_KEY=<your-api-key>  # Optional fallback
```

### 2. Login Flow

1. Navigate to `/auth/sign-in`
2. Enter username and password
3. On successful login:
   - JWT token stored in localStorage
   - User info stored in localStorage
   - Redirected to `/admin/default`

### 3. Protected Routes

All admin routes are protected and require authentication:
- `/admin/*` - Requires valid JWT token
- `/rtl/*` - Requires valid JWT token
- `/` - Redirects to login if not authenticated

### 4. Logout

Click the user avatar in the top right, then click "Log Out"

## 🔧 Development

### Adding New Users

Edit `be-form-extraction/services/auth_service.py`:

```python
fake_users_db = {
    "newuser": {
        "username": "newuser",
        "full_name": "New User",
        "email": "newuser@example.com",
        "hashed_password": "$2b$12$...",  # Use get_password_hash("password")
        "disabled": False,
        "role": "user",
        "created_at": datetime.now(),
    },
}
```

### Generating Password Hash

```python
from services.auth_service import get_password_hash
hashed = get_password_hash("my_password")
print(hashed)
```

### Changing Token Expiration

Edit `be-form-extraction/services/auth_service.py`:

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Change to desired duration
```

## 🛡️ Security Features

1. **Password Hashing:** Bcrypt with salt
2. **JWT Tokens:** HS256 algorithm
3. **Token Expiration:** 30 minutes (configurable)
4. **Role-Based Access:** Admin, User, Viewer roles
5. **Protected Routes:** Frontend route guards
6. **Secure Storage:** Tokens in localStorage (consider httpOnly cookies for production)

## 📊 Role Permissions

### Admin
- Full access to all features
- Can manage all resources
- Can view all data

### User
- Can upload images
- Can extract forms
- Can manage own data

### Viewer
- Read-only access
- Can view images
- Can view extraction results

## 🧪 Testing

### Test Login (Backend)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"tin.trantrung","password":"secret"}'
```

### Test Protected Endpoint
```bash
# Get token from login response
TOKEN="your-jwt-token"

curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Test Frontend
1. Start backend: `python main.py`
2. Start frontend: `npm start`
3. Navigate to `http://localhost:3000`
4. Should redirect to login page
5. Login with any account
6. Should redirect to dashboard

## 🚨 Troubleshooting

### "Could not validate credentials" Error
- Check if token is expired (30 min default)
- Verify API_SECRET_KEY is set correctly
- Clear localStorage and login again

### "Incorrect username or password"
- Verify username is correct (case-sensitive)
- Default password is "secret" for all demo accounts
- Check backend logs for authentication attempts

### Frontend Not Redirecting
- Clear browser localStorage
- Check browser console for errors
- Verify REACT_APP_API_URL is correct

## 📝 Production Considerations

1. **Change Default Passwords:** Update all user passwords
2. **Use Secure Secret Key:** Generate strong API_SECRET_KEY
3. **HTTPS Only:** Enable HTTPS for token transmission
4. **HttpOnly Cookies:** Consider using httpOnly cookies instead of localStorage
5. **Database:** Move from in-memory user store to real database
6. **Refresh Tokens:** Implement refresh token mechanism
7. **Rate Limiting:** Already implemented for login endpoint
8. **Session Management:** Implement session invalidation
9. **Audit Logging:** Log all authentication events
10. **Multi-Factor Auth:** Consider adding MFA for admin users

