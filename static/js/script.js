document.getElementById('profileForm').addEventListener('submit', async function(event) {
    event.preventDefault(); // Mencegah form dari reload halaman

    const pendidikan = document.getElementById('pendidikan').value;
    const pengalaman_kerja = document.getElementById('pengalaman_kerja').value;
    const keterampilan_komunikasi = document.getElementById('keterampilan_komunikasi').value;
    const problem_solving = document.getElementById('problem_solving').value;
    const gaji_harapan = document.getElementById('gaji_harapan').value;

    const response = await fetch('/match', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            pendidikan: pendidikan,
            pengalaman_kerja: pengalaman_kerja,
            keterampilan_komunikasi: keterampilan_komunikasi,
            problem_solving: problem_solving,
            gaji_harapan: gaji_harapan
        })
    });

    const result = await response.json();
    const resultDiv = document.getElementById('result');

    let htmlContent = `<h2>Skor Kecocokan: ${result.skor_kecocokan}%</h2>`;
    htmlContent += '<h3>Detail Perhitungan:</h3><ul>';
    result.penjelasan.forEach(item => {
        htmlContent += `<li>${item}</li>`;
    });
    htmlContent += '</ul>';

    resultDiv.innerHTML = htmlContent;
});