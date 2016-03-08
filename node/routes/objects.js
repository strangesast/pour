var express = require('express');
var router = express.Router();
var Kegerator = require('../models/kegerator');
var multer = require('multer');
var upload = multer();

router.get('/kegerators', function(req, res, next) {
  return Kegerator.find({}).then(function(kegerators) {
    return res.json(kegerators);
  }).catch(function(err) {
    return next(err);
  });
});

router.post('/kegerators', upload.array(), function(req, res, next) {
  var kegerator = new Kegerator(req.body);
  return Promise.resolve(kegerator.save()).then(function(result) {
    return res.json(req.body);
  }).catch(function(error) {
    if(error.name === "MongoError") {
      res.status(422);
      return res.json(error);
    }
    return next(error);
  });
});

module.exports = router;
