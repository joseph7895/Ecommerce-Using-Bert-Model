let rating = 0;

// Load products
if (document.getElementById("products")) {

fetch("http://127.0.0.1:5000/products")
.then(res=>res.json())
.then(data=>{

let container = document.getElementById("products");

data.forEach(item=>{
let div = document.createElement("div");
div.classList.add("product");

div.innerHTML = `
<img src="${item.image}">
<h4>${item.product_name}</h4>
<p>⭐ ${item.rating}</p>
`;

div.onclick=()=>{
localStorage.setItem("product",JSON.stringify(item));
window.location="product.html";
};

container.appendChild(div);
});

});
}

// Product page
if (document.getElementById("name")) {

let p = JSON.parse(localStorage.getItem("product"));

document.getElementById("img").src = p.image;
document.getElementById("name").innerText = p.product_name;
document.getElementById("rating").innerText = "⭐ "+p.rating;

}

// Stars
function setRating(r){
rating=r;
}

// Submit review
function submitReview(){

let review = document.getElementById("review").value;
let p = JSON.parse(localStorage.getItem("product"));

fetch("http://127.0.0.1:5000/sentiment",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({review:review})
})
.then(res=>res.json())
.then(data=>{

document.getElementById("result").innerHTML="Sentiment: "+data.sentiment;

// Recommendations
fetch("http://127.0.0.1:5000/recommend/"+p.category)
.then(res=>res.json())
.then(items=>{

let container = document.getElementById("recommend");
container.innerHTML="";

items.forEach(i=>{
let div=document.createElement("div");
div.classList.add("product");

div.innerHTML=`
<img src="${i.image}">
<h4>${i.product_name}</h4>
<p>⭐ ${i.rating}</p>
`;

container.appendChild(div);
});

});

});
}