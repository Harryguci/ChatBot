import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

const AccountPage = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    if (email) {
      return email[0].toUpperCase();
    }
    return "U";
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Account Settings
        </h1>
        <p className="text-gray-600">
          Manage your account information and preferences
        </p>
      </div>

      {/* Profile Card */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-center space-x-6 mb-6">
          {user?.picture_url ? (
            <img
              src={user.picture_url}
              alt={user.full_name || user.username}
              className="w-20 h-20 rounded-full border-2 border-gray-200"
            />
          ) : (
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center border-2 border-gray-200">
              <span className="text-white text-2xl font-medium">
                {getInitials(user?.full_name, user?.email)}
              </span>
            </div>
          )}
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">
              {user?.full_name || user?.username || "User"}
            </h2>
            <p className="text-gray-600">{user?.email}</p>
            <span
              className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${
                user?.role === "admin"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {user?.role?.toUpperCase() || "USER"}
            </span>
          </div>
        </div>
      </div>

      {/* Account Information */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">
          Account Information
        </h3>
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-500">
                Username
              </label>
              <p className="mt-1 text-gray-900">{user?.username || "N/A"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">Email</label>
              <p className="mt-1 text-gray-900">{user?.email || "N/A"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">
                Full Name
              </label>
              <p className="mt-1 text-gray-900">
                {user?.full_name || "Not provided"}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">
                User ID
              </label>
              <p className="mt-1 text-gray-900">{user?.id || "N/A"}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">
                Account Created
              </label>
              <p className="mt-1 text-gray-900">
                {formatDate(user?.created_at)}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-500">
                Last Login
              </label>
              <p className="mt-1 text-gray-900">
                {formatDate(user?.last_login) || "Never"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Account Status */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">
          Account Status
        </h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-gray-700">Account Status</span>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                user?.is_active
                  ? "bg-green-100 text-green-800"
                  : "bg-red-100 text-red-800"
              }`}
            >
              {user?.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-700">Verification Status</span>
            <span
              className={`px-3 py-1 rounded-full text-xs font-medium ${
                user?.is_verified
                  ? "bg-green-100 text-green-800"
                  : "bg-yellow-100 text-yellow-800"
              }`}
            >
              {user?.is_verified ? "Verified" : "Not Verified"}
            </span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">Actions</h3>
        <div className="flex space-x-4">
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
};

export default AccountPage;
