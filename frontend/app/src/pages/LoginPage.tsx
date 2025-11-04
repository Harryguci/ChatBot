import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Typography, message, Space } from "antd";
import { GoogleLogin, CredentialResponse } from "@react-oauth/google";
import { useAuth } from "../contexts/AuthContext";

const { Title, Text } = Typography;

const LoginPage = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    try {
      if (!credentialResponse.credential) {
        throw new Error("No credential received from Google");
      }

      await login(credentialResponse.credential);
      message.success("Login successful!");
      navigate("/", { replace: true });
    } catch (error: any) {
      console.error("Login error:", error);
      message.error(error.message || "Login failed. Please try again.");
    }
  };

  const handleGoogleError = () => {
    message.error("Google login failed. Please try again.");
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      }}
    >
      <Card
        style={{
          width: 400,
          borderRadius: 12,
          boxShadow: "0 10px 40px rgba(0,0,0,0.1)",
        }}
      >
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <div style={{ textAlign: "center" }}>
            <Title level={2} style={{ marginBottom: 8 }}>
              Welcome to Chatbot
            </Title>
            <Text type="secondary">
              Sign in with your Google account to continue
            </Text>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              marginTop: 24,
            }}
          >
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap
              text="signin_with"
              shape="rectangular"
              theme="outline"
              size="large"
            />
          </div>

          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              By signing in, you agree to our Terms of Service
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
