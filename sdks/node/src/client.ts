import axios, { AxiosInstance } from "axios";

export interface AuthResponse {
  user: Record<string, unknown>;
  access_token: string;
  refresh_token: string;
}

export interface PaymentResponse {
  id: string;
  status: string;
  reference: string;
  amount: number;
  currency: string;
  [key: string]: unknown;
}

export class ElcorpClient {
  private http: AxiosInstance;

  constructor(baseURL = "http://localhost:5000/api/v1", accessToken?: string) {
    this.http = axios.create({
      baseURL,
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    });
  }

  private setToken(token: string) {
    this.http.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  }

  // ---- Auth ----

  async signup(
    email: string,
    password: string,
    firstName: string,
    lastName: string
  ): Promise<AuthResponse> {
    const { data } = await this.http.post<AuthResponse>("/auth/signup", {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const { data } = await this.http.post<AuthResponse>("/auth/login", {
      email,
      password,
    });
    this.setToken(data.access_token);
    return data;
  }

  async refresh(refreshToken: string): Promise<{ access_token: string }> {
    const { data } = await this.http.post("/auth/refresh", {
      refresh_token: refreshToken,
    });
    this.setToken(data.access_token);
    return data;
  }

  // ---- Identity ----

  async getMe(): Promise<Record<string, unknown>> {
    const { data } = await this.http.get("/me");
    return data;
  }

  async updateMe(fields: Record<string, unknown>): Promise<Record<string, unknown>> {
    const { data } = await this.http.put("/me", fields);
    return data;
  }

  // ---- Payments ----

  async createPaymentToken(
    instrumentType: string,
    lastFour: string
  ): Promise<Record<string, unknown>> {
    const { data } = await this.http.post("/payments/tokens", {
      instrument_type: instrumentType,
      last_four: lastFour,
    });
    return data;
  }

  async createPayment(
    merchantId: string,
    amount: number,
    currency = "NAD",
    description = ""
  ): Promise<PaymentResponse> {
    const { data } = await this.http.post<PaymentResponse>("/payments", {
      merchant_id: merchantId,
      amount,
      currency,
      description,
    });
    return data;
  }

  async processPayment(paymentId: string): Promise<PaymentResponse> {
    const { data } = await this.http.post<PaymentResponse>(
      `/payments/${paymentId}/process`
    );
    return data;
  }

  async getPayment(paymentId: string): Promise<PaymentResponse> {
    const { data } = await this.http.get<PaymentResponse>(
      `/payments/${paymentId}`
    );
    return data;
  }

  async listPayments(
    page = 1
  ): Promise<{ items: PaymentResponse[]; total: number }> {
    const { data } = await this.http.get("/payments", { params: { page } });
    return data;
  }
}
