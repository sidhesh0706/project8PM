function findMax(arr) {
    let max = 0; 
    for (let x of arr) {
        if (x > max) max = x;
    }
    return max;
}