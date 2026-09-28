# South African Teachers Hub

A Flask platform for South African teachers, featuring product/vendor management, order tracking, and admin dashboard.

## Features

- 🛍️ **Product Management** - Add, edit, and manage products with categories
- 👥 **User Management** - Customer registration and authentication
- 🏪 **Vendor System** - Multi-vendor marketplace support
- 🚚 **Driver Management** - Delivery driver registration and tracking
- 📊 **Admin Dashboard** - Comprehensive admin panel with analytics
- 💰 **Accounting** - Built-in accounting and VAT management
- 📱 **Responsive Design** - Mobile-friendly interface with Tailwind CSS

## Tech Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL (Nile Database)
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Authentication**: Flask-Login
- **Deployment**: Vercel

## Setup Instructions

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd sath
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5004`

### Vercel deployment

Configure `SECRET_KEY` and one of `DATABASE_URL`, `POSTGRES_URL`, or
`NILEDB_URL` in the Vercel project settings. The application deliberately
refuses to use SQLite or a development secret on Vercel.

Initialize the production schema once, from a trusted machine with the same
database environment variable configured:

```bash
ADMIN_EMAIL=you@example.com \
ADMIN_PASSWORD='use-a-unique-password-of-at-least-12-characters' \
python init_production_db.py
```

This command creates or updates the schema without creating the local demo
accounts. `ADMIN_EMAIL` and `ADMIN_PASSWORD` are optional, but when supplied
they securely create or update the first administrator. Do not commit these
values. Files written to `/tmp` on Vercel are temporary; configure external
object storage before relying on user uploads in production.

### Default Admin Login
- **Email**: admin@brandcartel.com
- **Password**: admin123

## Deployment

This application is configured for deployment on Vercel with Nile Database.

### Prerequisites

1. **GitHub Repository**: your project repo
2. **Vercel Account**: Sign up at https://vercel.com
3. **Nile Database**: Configured and running

### Environment Variables (Vercel)

Set the following environment variables in your Vercel dashboard:

```
SECRET_KEY=your-production-secret-key-change-this
POSTGRES_URL=postgres://your-user:your-password@your-host/your-database
NILEDB_URL=postgres://your-user:your-password@your-host/your-database
NILEDB_USER=your-nile-user
NILEDB_PASSWORD=your-nile-password
NILEDB_API_URL=https://your-region.api.thenile.dev/v2/databases/your-database-id
NILEDB_POSTGRES_URL=postgres://your-host/your-database
```

### Quick Deploy to Vercel

1. **Push to GitHub** ✅ (Already completed)
   ```bash
   git push origin main
   ```

2. **Deploy to Vercel**:
   - Visit: https://vercel.com/new
   - Import from GitHub: your project repo
   - Add environment variables from above
   - Deploy!

3. **Alternative - Vercel CLI**:
   ```bash
   npm i -g vercel
   vercel --prod
   ```

### Database Setup

The application will automatically:
- Connect to Nile Database using the provided credentials
- Initialize database schema on first run
- Create admin user: admin@brandcartel.com / admin123

### Post-Deployment

After deployment:
1. Visit your Vercel domain
2. Login with admin credentials
3. Configure site settings in admin panel
4. Add products and categories
5. Start selling!

## Database

The application uses Nile Database (PostgreSQL) for production and SQLite for local development. The database schema is automatically created on first run.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
