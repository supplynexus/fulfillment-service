// 测试前端 token
const token = localStorage.getItem('access_token');
console.log('Token:', token);

if (token) {
  const parts = token.split('.');
  if (parts.length === 3) {
    const payload = JSON.parse(atob(parts[1]));
    console.log('Token payload:', payload);
    console.log('Token expired:', payload.exp < Math.floor(Date.now() / 1000));
  }
}
