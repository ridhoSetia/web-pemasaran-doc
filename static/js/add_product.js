// Elemen DOM
const selectKategori = document.getElementById("kategori");
const containerKategoriBaru = document.getElementById(
  "kategori_baru_container",
);
const inputKategoriBaru = document.getElementById("kategori_baru");
const inputKodeUnik = document.getElementById("kode_unik");

// Fungsi 1: Menangani visibilitas form kategori baru
function toggleKategoriBaru() {
  if (selectKategori.value === "BARU") {
    containerKategoriBaru.classList.remove("hidden");
    inputKategoriBaru.setAttribute("required", "true");
    inputKategoriBaru.focus();
  } else {
    containerKategoriBaru.classList.add("hidden");
    inputKategoriBaru.removeAttribute("required");
    inputKategoriBaru.value = ""; // Bersihkan input jika batal
  }

  // Setiap kali dropdown berubah, jalankan juga generator SKU
  generateKodeUnik();
}

// Fungsi 2: Generator Kode Unik Real-time
function generateKodeUnik() {
  let teksKategori = "";

  // Tentukan dari mana kita mengambil teks kategori
  if (selectKategori.value === "BARU") {
    teksKategori = inputKategoriBaru.value;
  } else {
    teksKategori = selectKategori.value;
  }

  // Jika teks kategori kosong, kosongkan juga kode uniknya
  if (teksKategori.trim() === "") {
    inputKodeUnik.value = "";
    return;
  }

  // Ambil maksimal 3 karakter pertama, hilangkan spasi, dan jadikan huruf kapital
  let prefix = teksKategori.replace(/\s+/g, "").substring(0, 3).toUpperCase();

  // Ciptakan 4 angka acak (dari 1000 hingga 9999) untuk keunikan
  let angkaAcak = Math.floor(100 + Math.random() * 900);

  // Gabungkan menjadi format SKU (Contoh: DOC-8492)
  inputKodeUnik.value = `${prefix}-${angkaAcak}`;
}

// Event Listeners (Pemicu Real-time)

// 1. Pemicu saat input "Kategori Baru" sedang diketik (Setiap kali tuts keyboard ditekan)
inputKategoriBaru.addEventListener("input", generateKodeUnik);

// 2. Pemicu saat dropdown kategori diubah
selectKategori.addEventListener("change", toggleKategoriBaru);