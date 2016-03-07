var express = require('express');
var router = express.Router();
var qs = require('querystring');
var Kegerator = require('../models/kegerator');

router.get('/kegerators', function(req, res, next) {
  return Kegerator.find({}).then(function(kegerators) {
    return res.json(kegerators);
  }).catch(function(err) {
    return next(err);
  });
});

router.post('/kegerators', function(req, res, next) {
  console.log(req.body);
  var postData = qs.parse(req.body);
  console.log(postData);
  return res.json(postData);
});

module.exports = router;
